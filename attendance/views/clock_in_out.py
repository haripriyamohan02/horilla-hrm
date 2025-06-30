"""
clock_in_out.py

This module is used register endpoints to the check-in check-out functionalities
"""

import ipaddress
import logging

logger = logging.getLogger(__name__)
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from attendance.methods.utils import (
    activity_datetime,
    employee_exists,
    format_time,
    overtime_calculation,
    shift_schedule_today,
    strtime_seconds,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceGeneralSetting,
    AttendanceLateComeEarlyOut,
    GraceTime,
)
from base.context_processors import (
    enable_late_come_early_out_tracking,
    timerunner_enabled,
)
import os
from base.models import AttendanceAllowedIP, Company, EmployeeShiftDay
from horilla.decorators import hx_request_required, login_required
from horilla.horilla_middlewares import _thread_locals

# Configure logging specifically for biometric attendance
def setup_biometric_logger():
    """Setup dedicated logger for biometric attendance operations"""
    logger = logging.getLogger('biometric_attendance')
    
    # Avoid adding multiple handlers if logger already exists
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create file handler with timestamp in filename
        log_filename = f"{log_dir}/biometric_attendance_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
    
    return logger

def late_come_create(attendance):
    """
    used to create late come report
    args:
        attendance : attendance object
    """

    if AttendanceLateComeEarlyOut.objects.filter(
        type="late_come", attendance_id=attendance
    ).exists():
        late_come_obj = AttendanceLateComeEarlyOut.objects.filter(
            type="late_come", attendance_id=attendance
        ).first()
    else:
        late_come_obj = AttendanceLateComeEarlyOut()

    late_come_obj.type = "late_come"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def late_come(attendance, start_time, end_time, shift):
    """
    this method is used to mark the late check-in  attendance after the shift starts
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        end_time : attendance day shift end time

    """
    if not enable_late_come_early_out_tracking(None).get("tracking"):
        return
    request = getattr(_thread_locals, "request", None)
    now_sec = strtime_seconds(attendance.attendance_clock_in.strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")

    # Checking gracetime allowance before creating late come
    if shift and shift.grace_time_id:
        # checking grace time in shift, it has the higher priority
        if (
            shift.grace_time_id.is_active == True
            and shift.grace_time_id.allowed_clock_in == True
        ):
            # Setting allowance for the check in time
            now_sec -= shift.grace_time_id.allowed_time_in_secs
    # checking default grace time
    elif GraceTime.objects.filter(is_default=True, is_active=True).exists():
        grace_time = GraceTime.objects.filter(
            is_default=True,
            is_active=True,
        ).first()
        # Setting allowance for the check in time if grace allocate for clock in event
        if grace_time.allowed_clock_in:
            now_sec -= grace_time.allowed_time_in_secs
    else:
        pass
    if start_time > end_time and start_time != end_time:
        # night shift
        if now_sec < mid_day_sec:
            # Here  attendance or attendance activity for new day night shift
            late_come_create(attendance)
        elif now_sec > start_time:
            # Here  attendance or attendance activity for previous day night shift
            late_come_create(attendance)
    elif start_time < now_sec:
        late_come_create(attendance)
    return True


def clock_in_attendance_and_activity(
    employee,
    date_today,
    attendance_date,
    day,
    now,
    shift,
    minimum_hour,
    start_time,
    end_time,
    in_datetime,
):
    """
    This method is used to create attendance activity or attendance when an employee clocks-in
    args:
        employee        : employee instance
        date_today      : date
        attendance_date : the date that attendance for
        day             : shift day
        now             : current time
        shift           : shift object
        minimum_hour    : minimum hour in shift schedule
        start_time      : start time in shift schedule
        end_time        : end time in shift schedule
    """
    # attendance activity create
    open_activity = AttendanceActivity.objects.filter(
        employee_id=employee,
        attendance_date=attendance_date,
        clock_out=None,
    ).first()

    if not open_activity:
        AttendanceActivity.objects.create(
            employee_id=employee,
            attendance_date=attendance_date,
            clock_in_date=date_today,
            shift_day=day,
            clock_in=in_datetime,
            in_datetime=in_datetime,
        )
    # create attendance if not exist
    attendance = Attendance.objects.filter(
        employee_id=employee, attendance_date=attendance_date
    )
    if not attendance.exists():
        attendance = Attendance()
        attendance.employee_id = employee
        attendance.shift_id = shift
        attendance.work_type_id = attendance.employee_id.employee_work_info.work_type_id
        attendance.attendance_date = attendance_date
        attendance.attendance_day = day
        attendance.attendance_clock_in = now
        attendance.attendance_clock_in_date = date_today
        attendance.minimum_hour = minimum_hour
        attendance.save()
        # check here late come or not

        attendance = Attendance.find(attendance.id)
        late_come(
            attendance=attendance, start_time=start_time, end_time=end_time, shift=shift
        )
    else:
        attendance = attendance[0]
        attendance.attendance_clock_out = None
        attendance.attendance_clock_out_date = None
        attendance.save()
        # delete if the attendance marked the early out
        early_out_instance = attendance.late_come_early_out.filter(type="early_out")
        if early_out_instance.exists():
            early_out_instance[0].delete()
    return attendance


@login_required
@hx_request_required
def clock_in(request):
    """
    This method is used to mark the attendance once per a day and multiple attendance activities.
    """
    biometric_logger = setup_biometric_logger()
    # check wether check in/check out feature is enabled
    selected_company = request.session.get("selected_company")
    if selected_company == "all":
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=None
        ).first()
    else:
        company = Company.objects.filter(id=selected_company).first()
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=company
        ).first()
    # request.__dict__.get("datetime")' used to check if the request is from a biometric device
    biometric_logger.info("=" * 60)
    biometric_logger.info("IP VALIDATION PROCESS STARTED")
    biometric_logger.info("=" * 60)
    if (
        attendance_general_settings
        and attendance_general_settings.enable_check_in
        or request.__dict__.get("datetime")
    ):
        biometric_logger.info("STEP 2: Retrieving allowed IP settings")
        allowed_attendance_ips = AttendanceAllowedIP.objects.first()
        biometric_logger.debug(f"allowed_attendance_ips found: {bool(allowed_attendance_ips)}")
        biometric_logger.debug(f"if condition data: {request, allowed_attendance_ips}")
        if (
            not request.__dict__.get("datetime")
            and allowed_attendance_ips
            and allowed_attendance_ips.is_enabled
            and hasattr(request, 'META')
            and isinstance(request.META, dict)  # This is the key fix
        ):
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR") if hasattr(request.META, 'get') else None
            ip = request.META.get("REMOTE_ADDR") if hasattr(request.META, 'get') else None
            
            biometric_logger.debug(f"HTTP_X_FORWARDED_FOR: {x_forwarded_for}")
            biometric_logger.debug(f"REMOTE_ADDR: {ip}")
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0]

            allowed_ips = allowed_attendance_ips.additional_data.get("allowed_ips", [])
            ip_allowed = False
            for allowed_ip in allowed_ips:
                try:
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(
                        allowed_ip, strict=False
                    ):
                        ip_allowed = True
                        break
                except ValueError:
                    continue

            if not ip_allowed:
                return HttpResponse(_("You cannot mark attendance from this network"))

        # --- Begin fix for biometric punch-in always creating attendance ---
        is_biometric = request.__dict__.get("datetime") is not None
        if is_biometric:
            biometric_logger.info("=" * 60)
            biometric_logger.info("BIOMETRIC ATTENDANCE PROCESS STARTED")
            biometric_logger.info("=" * 60)
            
            try:
                # Step 1: Employee Resolution
                biometric_logger.info("STEP 1: Resolving employee from request.user")
                biometric_logger.debug(f"Request user: {getattr(request, 'user', 'No user found')}")
                
                employee, work_info = employee_exists(request)
                
                if not employee:
                    biometric_logger.error("Employee resolution failed - No employee found")
                    return HttpResponse(_("Biometric punch could not resolve employee or work info."))
                
                if not work_info:
                    biometric_logger.error("Work info resolution failed - No work info found")
                    biometric_logger.debug(f"Employee found: {employee}, but work_info is None")
                    return HttpResponse(_("Biometric punch could not resolve employee or work info."))
                
                biometric_logger.info(f"Employee successfully resolved: {employee}")
                biometric_logger.info(f"Work info successfully resolved: {work_info}")
                biometric_logger.debug(f"Employee ID: {getattr(employee, 'id', 'No ID')}")
                biometric_logger.debug(f"Work info shift: {getattr(work_info, 'shift_id', 'No shift')}")
                
                # Step 2: DateTime Processing
                biometric_logger.info("STEP 2: Processing datetime information")
                datetime_now = request.datetime
                biometric_logger.debug(f"Request datetime: {datetime_now}")
                
                shift = work_info.shift_id
                biometric_logger.info(f"Shift assigned: {shift}")
                
                date_today = request.date if hasattr(request, "date") else datetime_now.date()
                biometric_logger.debug(f"Date today determined: {date_today}")
                biometric_logger.debug(f"Used request.date: {hasattr(request, 'date')}")
                
                attendance_date = date_today
                biometric_logger.debug(f"Attendance date set: {attendance_date}")
                
                # Step 3: Day Processing
                biometric_logger.info("STEP 3: Processing day information")
                day = date_today.strftime("%A").lower()
                biometric_logger.debug(f"Day string generated: {day}")
                
                day_obj, day_created = EmployeeShiftDay.objects.get_or_create(day=day)
                biometric_logger.info(f"Day object {'created' if day_created else 'retrieved'}: {day_obj}")
                
                # Step 4: Time Processing
                biometric_logger.info("STEP 4: Processing time information")
                now = request.time.strftime("%H:%M") if hasattr(request, "time") else datetime_now.strftime("%H:%M")
                biometric_logger.debug(f"Current time determined: {now}")
                biometric_logger.debug(f"Used request.time: {hasattr(request, 'time')}")
                
                # Step 5: Shift Schedule
                biometric_logger.info("STEP 5: Getting shift schedule for today")
                biometric_logger.debug(f"Calling shift_schedule_today with day={day_obj}, shift={shift}")
                
                minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                    day=day_obj, shift=shift
                )
                biometric_logger.info(f"Shift schedule retrieved - Min hours: {minimum_hour}, Start: {start_time_sec}, End: {end_time_sec}")
                
                # Step 6: Attendance Processing
                biometric_logger.info("STEP 6: Processing attendance record")
                biometric_logger.debug(f"Searching for existing attendance - Employee: {employee}, Date: {attendance_date}")
                
                attendance = Attendance.objects.filter(
                    employee_id=employee, attendance_date=attendance_date
                ).first()
                
                if not attendance:
                    biometric_logger.info("No existing attendance found - Creating new attendance record")
                    
                    attendance = Attendance()
                    attendance.employee_id = employee
                    attendance.shift_id = shift
                    attendance.work_type_id = work_info.work_type_id
                    attendance.attendance_date = attendance_date
                    attendance.attendance_day = day_obj
                    attendance.attendance_clock_in = now
                    attendance.attendance_clock_in_date = date_today
                    attendance.minimum_hour = minimum_hour
                    
                    biometric_logger.debug("Attendance object populated with data")
                    biometric_logger.debug(f"- Employee ID: {employee}")
                    biometric_logger.debug(f"- Shift ID: {shift}")
                    biometric_logger.debug(f"- Work Type ID: {work_info.work_type_id}")
                    biometric_logger.debug(f"- Attendance Date: {attendance_date}")
                    biometric_logger.debug(f"- Day: {day_obj}")
                    biometric_logger.debug(f"- Clock In: {now}")
                    biometric_logger.debug(f"- Clock In Date: {date_today}")
                    biometric_logger.debug(f"- Minimum Hour: {minimum_hour}")
                    
                    attendance.save()
                    biometric_logger.info(f"New attendance record saved with ID: {attendance.id}")
                    
                    # Refresh attendance object
                    attendance = Attendance.find(attendance.id)
                    biometric_logger.debug("Attendance object refreshed from database")
                    
                    # Step 7: Late Come Processing
                    biometric_logger.info("STEP 7: Processing late come calculation")
                    biometric_logger.debug(f"Calling late_come with attendance={attendance.id}, start_time={start_time_sec}, end_time={end_time_sec}, shift={shift}")
                    
                    late_come(
                        attendance=attendance, start_time=start_time_sec, end_time=end_time_sec, shift=shift
                    )
                    biometric_logger.info("Late come calculation completed")
                else:
                    biometric_logger.info(f"Existing attendance found with ID: {attendance.id}")
                    biometric_logger.debug(f"Existing attendance details - Clock in: {attendance.attendance_clock_in}, Date: {attendance.attendance_date}")
                
                # Step 8: Attendance Activity Processing
                biometric_logger.info("STEP 8: Processing attendance activity")
                biometric_logger.debug(f"Searching for open activity - Employee: {employee}, Date: {attendance_date}")
                
                open_activity = AttendanceActivity.objects.filter(
                    employee_id=employee,
                    attendance_date=attendance_date,
                    clock_out=None
                ).first()
                
                if not open_activity:
                    biometric_logger.info("No open activity found - Creating new attendance activity")
                    
                    activity_data = {
                        'employee_id': employee,
                        'attendance_date': attendance_date,
                        'clock_in_date': date_today,
                        'shift_day': day_obj,
                        'clock_in': datetime_now,
                        'in_datetime': datetime_now,
                    }
                    
                    biometric_logger.debug("Activity data prepared:")
                    for key, value in activity_data.items():
                        biometric_logger.debug(f"- {key}: {value}")
                    
                    new_activity = AttendanceActivity.objects.create(**activity_data)
                    biometric_logger.info(f"New attendance activity created with ID: {new_activity.id}")
                    
                else:
                    biometric_logger.info(f"Open activity exists with ID: {open_activity.id} - No new activity created")
                    biometric_logger.debug(f"Open activity details - Clock in: {open_activity.clock_in}, Date: {open_activity.attendance_date}")
                
                # Step 9: Response
                biometric_logger.info("STEP 9: Rendering response")
                biometric_logger.info("Biometric attendance process completed successfully")
                biometric_logger.info("=" * 60)
                
                return render(request, "attendance/components/in_out_component.html")
                
            except Exception as e:
                biometric_logger.error("=" * 60)
                biometric_logger.error("BIOMETRIC ATTENDANCE PROCESS FAILED")
                biometric_logger.error(f"Error: {str(e)}")
                biometric_logger.error(f"Error type: {type(e).__name__}")
                biometric_logger.exception("Full exception traceback:")
                biometric_logger.error("=" * 60)
                raise
        # --- End fix for biometric punch-in always creating attendance ---

        # UI or other punch-in logic (unchanged)
        employee, work_info = employee_exists(request)
        datetime_now = datetime.now()
        if request.__dict__.get("datetime"):
            datetime_now = request.datetime
        if employee and work_info is not None:
            shift = work_info.shift_id
            date_today = date.today()
            if request.__dict__.get("date"):
                date_today = request.date
            attendance_date = date_today
            day = date_today.strftime("%A").lower()
            day, _ = EmployeeShiftDay.objects.get_or_create(day=day)
            now = datetime_now.strftime("%H:%M")
            minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                day=day, shift=shift
            )
            attendance = clock_in_attendance_and_activity(
                employee=employee,
                date_today=date_today,
                attendance_date=attendance_date,
                day=day,
                now=now,
                shift=shift,
                minimum_hour=minimum_hour,
                start_time=start_time_sec,
                end_time=end_time_sec,
                in_datetime=datetime_now,
            )
            return render(request, "attendance/components/in_out_component.html")
        return render(request, "attendance/components/in_out_component.html")
    else:
        messages.error(request, _( "Check in/Check out feature is not enabled."))
        return render(request, "attendance/components/in_out_component.html")


def clock_out_attendance_and_activity(
    employee, work_info, date_today, now, out_datetime=None, is_biometric=False
):
    """
    Clock out the attendance and activity
    args:
        employee    : employee instance
        date_today  : today date
        now         : now
    """
    attendance_activities = (
        AttendanceActivity.objects.filter(
            employee_id=employee,
        )
        .order_by("attendance_date", "id")
        .select_related("employee_id")
    )
    attendance_activity = None  # Initialize attendance_activity

    if attendance_activities.filter(clock_out__isnull=True).exists():
        attendance_activity = attendance_activities.filter(clock_out__isnull=True).last()
        attendance_activity.clock_out = out_datetime
        attendance_activity.clock_out_date = attendance_activity.attendance_date
        attendance_activity.out_datetime = out_datetime
        attendance_activity.save()

        attendance_activities = attendance_activities.filter(
            attendance_date=attendance_activity.attendance_date
        )
        # Here calculate the total durations between the attendance activities

        duration = 0
        for activity in attendance_activities:
            in_datetime, out_datetime = activity_datetime(activity)
            if not (in_datetime and out_datetime):
                continue
            difference = out_datetime - in_datetime
            days_second = difference.days * 24 * 3600
            seconds = difference.seconds
            total_seconds = days_second + seconds
            duration = duration + total_seconds
        duration = format_time(duration)
        # update clock out of attendance
        attendance = Attendance.objects.filter(
            employee_id=employee, attendance_date=attendance_activity.attendance_date
        ).first()
        if not attendance:
            logger.error(
                "Attendance record not found for activity %s", attendance_activity.id
            )
            return None
        
        # Only update attendance check-in and check-out if the dates match
        if attendance.attendance_clock_in_date == attendance_date:
            attendance.attendance_clock_out = now + ":00"
            attendance.attendance_clock_out_date = attendance_date
            attendance.attendance_worked_hour = duration
            attendance.attendance_overtime = overtime_calculation(attendance)
            attendance.attendance_validated = True
            attendance.save()

        return attendance
    elif is_biometric:
        shift = work_info.shift_id
        attendance_date = date_today
        day = date_today.strftime("%A").lower()
        day, _ = EmployeeShiftDay.objects.get_or_create(day=day)

        minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
            day=day, shift=shift
        )
        now_sec = strtime_seconds(now)
        mid_day_sec = strtime_seconds("12:00")

        if start_time_sec > end_time_sec and now_sec < mid_day_sec:
            attendance_date = date_today - timedelta(days=1)
            day = attendance_date.strftime("%A").lower()
            day, _ = EmployeeShiftDay.objects.get_or_create(day=day)
            minimum_hour, _, _ = shift_schedule_today(day=day, shift=shift)

        attendance, created = Attendance.objects.get_or_create(
            employee_id=employee,
            attendance_date=attendance_date,
            defaults={
                "shift_id": shift,
                "work_type_id": work_info.work_type_id,
                "attendance_day": day,
                "minimum_hour": minimum_hour,
            },
        )

        AttendanceActivity.objects.create(
            employee_id=employee,
            attendance_date=attendance_date,
            clock_out_date=attendance_date,
            shift_day=day,
            clock_out=out_datetime,
            out_datetime=out_datetime,
        )

        attendance_activities = AttendanceActivity.objects.filter(
            employee_id=employee, attendance_date=attendance_date
        )

        duration = 0
        for activity in attendance_activities:
            in_datetime, out_datetime = activity_datetime(activity)
            if not (in_datetime and out_datetime):
                continue
            difference = out_datetime - in_datetime
            days_second = difference.days * 24 * 3600
            seconds = difference.seconds
            total_seconds = days_second + seconds
            duration = duration + total_seconds

        duration = format_time(duration)
        
        # Only update attendance check-in and check-out if the dates match
        if attendance.attendance_clock_in_date == attendance_date:
            attendance.attendance_clock_out = now + ":00"
            attendance.attendance_clock_out_date = attendance_date
            attendance.attendance_worked_hour = duration
            attendance.attendance_overtime = overtime_calculation(attendance)
            attendance.attendance_validated = True
            attendance.save()
            
        return attendance
    logger.error("No attendance clock in activity found that needs clocking out.")
    return


def early_out_create(attendance):
    """
    Used to create early out report
    args:
        attendance : attendance obj
    """
    if AttendanceLateComeEarlyOut.objects.filter(
        type="early_out", attendance_id=attendance
    ).exists():
        late_come_obj = AttendanceLateComeEarlyOut.objects.filter(
            type="early_out", attendance_id=attendance
        ).first()
    else:
        late_come_obj = AttendanceLateComeEarlyOut()
    late_come_obj.type = "early_out"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def early_out(attendance, start_time, end_time, shift):
    """
    This method is used to mark the early check-out attendance before the shift ends
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        start_end : attendance day shift end time
    """
    if not enable_late_come_early_out_tracking(None).get("tracking"):
        return

    clock_out_time = attendance.attendance_clock_out
    if isinstance(clock_out_time, str):
        clock_out_time = datetime.strptime(clock_out_time, "%H:%M:%S")

    now_sec = strtime_seconds(clock_out_time.strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")
    # Checking gracetime allowance before creating early out
    if shift and shift.grace_time_id:
        if (
            shift.grace_time_id.is_active == True
            and shift.grace_time_id.allowed_clock_out == True
        ):
            now_sec += shift.grace_time_id.allowed_time_in_secs
    elif GraceTime.objects.filter(is_default=True, is_active=True).exists():
        grace_time = GraceTime.objects.filter(
            is_default=True,
            is_active=True,
        ).first()
        # Setting allowance for the check out time if grace allocate for clock out event
        if grace_time.allowed_clock_out:
            now_sec += grace_time.allowed_time_in_secs
    else:
        pass
    if start_time > end_time:
        # Early out condition for night shift
        if now_sec < mid_day_sec:
            if now_sec < end_time:
                # Early out condition for general shift
                early_out_create(attendance)
        else:
            early_out_create(attendance)
        return
    if end_time > now_sec:
        early_out_create(attendance)
    return


@login_required
@hx_request_required
def clock_out(request):
    """
    This method is used to set the out date and time for attendance and attendance activity
    """
    biometric_logger = setup_biometric_logger()
    # check wether check in/check out feature is enabled
    selected_company = request.session.get("selected_company")
    if selected_company == "all":
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=None
        ).first()
    else:
        company = Company.objects.filter(id=selected_company).first()
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=company
        ).first()
    if (
        attendance_general_settings
        and attendance_general_settings.enable_check_in
        or request.__dict__.get("datetime")
    ):
        datetime_now = datetime.now()
        if request.__dict__.get("datetime"):
            datetime_now = request.datetime
        employee, work_info = employee_exists(request)

        if not work_info:
            return render(request, "attendance/components/in_out_component.html")

        shift = work_info.shift_id
        date_today = date.today()
        if request.__dict__.get("date"):
            date_today = request.date
        day = date_today.strftime("%A").lower()
        day, _ = EmployeeShiftDay.objects.get_or_create(day=day)
        attendance = (
            Attendance.objects.filter(employee_id=employee)
            .order_by("id", "attendance_date")
            .last()
        )
        if attendance is not None:
            day = attendance.attendance_day
        now = datetime.now().strftime("%H:%M")
        if request.__dict__.get("time"):
            now = request.time.strftime("%H:%M")
        minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
            day=day, shift=shift
        )
        is_biometric = request.__dict__.get("datetime") is not None
        attendance = clock_out_attendance_and_activity(
            employee=employee,
            work_info=work_info,
            date_today=date_today,
            now=now,
            out_datetime=datetime_now,
            is_biometric=is_biometric,
        )
        if attendance:
            early_out_instance = attendance.late_come_early_out.filter(type="early_out")
            is_night_shift = attendance.is_night_shift()
            next_date = attendance.attendance_date + timedelta(days=1)
            if not early_out_instance.exists():
                if is_night_shift:
                    now_sec = strtime_seconds(now)
                    mid_sec = strtime_seconds("12:00")

                    if (attendance.attendance_date == date_today) or (
                        # check is next day mid
                        mid_sec >= now_sec
                        and date_today == next_date
                    ):
                        early_out(
                            attendance=attendance,
                            start_time=start_time_sec,
                            end_time=end_time_sec,
                            shift=shift,
                        )
                elif attendance.attendance_date == date_today:
                    early_out(
                        attendance=attendance,
                        start_time=start_time_sec,
                        end_time=end_time_sec,
                        shift=shift,
                    )

        return render(request, "attendance/components/in_out_component.html")
    else:
        messages.error(request, _("Check in/Check out feature is not enabled."))
        return render(request, "attendance/components/in_out_component.html")

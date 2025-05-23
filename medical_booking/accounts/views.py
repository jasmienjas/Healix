from rest_framework import generics, status
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import datetime, timedelta
from django.db.models import Q
from django.db.utils import IntegrityError

import logging
import os

from .models import CustomUser, DoctorProfile, PatientProfile, Appointment, DoctorAvailability
from .serializers import (
    UserSerializer,
    PatientRegisterSerializer,
    DoctorRegisterSerializer,
    AppointmentSerializer,
    DoctorProfileSerializer
)
from .token_serializers import CustomTokenObtainPairSerializer

logger = logging.getLogger(__name__)

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class PatientRegisterView(generics.CreateAPIView):
    serializer_class = PatientRegisterSerializer
    
    def create(self, request, *args, **kwargs):
        # Log the incoming request data
        print("Received data:", request.data)
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # Log validation errors
            print("Validation errors:", serializer.errors)
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = serializer.save()
            return Response({
                'success': True,
                'message': 'Registration successful',
                'data': {
                    'id': user.id,
                    'email': user.email,
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'user_type': 'patient'
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            print("Error during registration:", str(e))
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
class DoctorRegisterView(generics.CreateAPIView):
    """
    View for doctor registration.
    """
    serializer_class = DoctorRegisterSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Registration successful. Please wait for admin approval.',
            'data': {
                'id': user.id,
                'email': user.email,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'user_type': 'doctor'
            }
        })

class DoctorListView(APIView):
    def get(self, request):
        doctors = CustomUser.objects.filter(user_type='doctor')
        doctor_data = []

        for doctor in doctors:
            try:
                profile = doctor.doctorprofile
                doctor_data.append({
                    "id": doctor.id,
                    "full_name": f"{doctor.first_name} {doctor.last_name}".strip() or doctor.username,
                    "specialty": profile.specialty,
                })
            except DoctorProfile.DoesNotExist:
                pass

        return Response(doctor_data)

class PostponeAppointmentView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        
        # Ensure that only doctors can postpone appointments
        if request.user.user_type != 'doctor':
            return Response({
                'success': False,
                'message': 'Only doctors can postpone appointments.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        new_datetime_str = request.data.get('appointment_datetime')
        postpone_reason = request.data.get('postpone_reason')

        if not new_datetime_str:
            return Response({
                'success': False,
                'message': 'New appointment datetime is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if not postpone_reason:
            return Response({
                'success': False,
                'message': 'A postpone reason is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_datetime = datetime.fromisoformat(new_datetime_str)
        except Exception:
            return Response({
                'success': False,
                'message': 'Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS).'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.appointment_datetime = new_datetime
        appointment.status = 'postponed'
        appointment.reason = postpone_reason
        appointment.reason = postpone_reason
        appointment.save()
        
        # Send email notification to patient
        try:
            subject = "Appointment Postponed"
            message = (
                f"Dear {appointment.patient.user.first_name},\n\n"
                f"Your appointment with Dr. {appointment.doctor.user.first_name} {appointment.doctor.user.last_name} "
                f"has been postponed to {new_datetime}.\n\n"
                f"Reason: {postpone_reason}\n\n"
                f"Best regards,\nHealix Team"
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [appointment.patient.user.email]
            )
        except Exception as e:
            logger.error(f"Failed to send postponement email: {e}")
        
        serializer = AppointmentSerializer(appointment)
        return Response({
            'success': True,
            'message': 'Appointment postponed successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

class CancelAppointmentView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        
        if request.user.user_type != 'doctor':
            return Response({
                'success': False,
                'message': 'Only doctors can cancel appointments.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        cancellation_message = request.data.get('cancellation_message')
        if not cancellation_message:
            return Response({
                'success': False,
                'message': 'Cancellation message is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.status = 'cancelled'
        appointment.reason = cancellation_message
        appointment.reason = cancellation_message
        appointment.save()
        
        # Send email notification
        try:
            subject = "Appointment Cancellation Notice"
            message = (
                f"Dear {appointment.patient.user.first_name},\n\n"
                f"Your appointment scheduled on {appointment.appointment_datetime} "
                f"has been cancelled by Dr. {appointment.doctor.user.first_name} {appointment.doctor.user.last_name}.\n\n"
                f"Message from doctor: {cancellation_message}\n\n"
                f"Best regards,\nHealix Team"
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [appointment.patient.user.email]
            )
        except Exception as e:
            logger.error(f"Failed to send cancellation email: {e}")
        
        serializer = AppointmentSerializer(appointment)
        return Response({
            'success': True,
            'message': 'Appointment cancelled successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

class PatientScheduleView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(patient__user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'message': 'Appointments retrieved successfully',
            'data': serializer.data
        })

class DoctorApprovalStatusView(APIView):
    """
    View to check doctor approval status
    """
    def get(self, request, email):
        try:
            doctor = DoctorProfile.objects.get(user__email=email)
            return Response({
                'success': True,
                'status': 'approved' if doctor.is_approved else 'pending'
            })
        except DoctorProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Doctor not found'
            }, status=status.HTTP_404_NOT_FOUND)

class DoctorScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            if request.user.user_type != 'doctor':
                return Response({
                    'success': False,
                    'message': 'Only doctors can access this endpoint'
                }, status=status.HTTP_403_FORBIDDEN)

            print(f"Fetching appointments for doctor: {request.user.id}")  # Debug log
            
            doctor_profile = request.user.doctor_profile
            appointments = Appointment.objects.filter(
                doctor=doctor_profile
            ).select_related(
                'patient__user',
                'doctor__user'
            )
            
            print(f"Found {appointments.count()} appointments")  # Debug log
            
            serializer = AppointmentSerializer(appointments, many=True)
            serialized_data = serializer.data
            print(f"Serialized data: {serialized_data}")  # Debug log
            
            return Response({
                'success': True,
                'message': 'Appointments retrieved successfully',
                'data': serialized_data
            })
        except Exception as e:
            print(f"Error in DoctorScheduleView: {str(e)}")  # Debug log
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DoctorSearchView(generics.ListAPIView):
    serializer_class = DoctorProfileSerializer
    permission_classes = []  # Allow public access

    def get_queryset(self):
        queryset = DoctorProfile.objects.filter(is_approved=True)
        
        name = self.request.query_params.get('name', None)
        specialty = self.request.query_params.get('specialty', None)
        location = self.request.query_params.get('location', None)

        if name:
            queryset = queryset.filter(
                Q(user__first_name__icontains=name) |
                Q(user__last_name__icontains=name)
            )
        
        if specialty:
            queryset = queryset.filter(specialty__icontains=specialty)
            
        if location:
            queryset = queryset.filter(office_address__icontains=location)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'message': 'Doctors retrieved successfully',
            'data': serializer.data
        })

class DoctorProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            if request.user.user_type != 'doctor':
                return Response({
                    'success': False,
                    'message': 'Only doctors can access this endpoint'
                }, status=status.HTTP_403_FORBIDDEN)

            doctor_profile = request.user.doctor_profile
            serializer = DoctorProfileSerializer(doctor_profile)
            
            return Response({
                'success': True,
                'message': 'Profile retrieved successfully',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DoctorAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logger.info(f"DoctorAvailabilityView accessed by user: {request.user.id}")
            
            if request.user.user_type != 'doctor':
                logger.warning(f"Non-doctor user {request.user.id} attempted to access availability")
                return Response({
                    'success': False,
                    'message': 'Only doctors can access this endpoint'
                }, status=status.HTTP_403_FORBIDDEN)

            # Get query parameters
            year = int(request.query_params.get('year', datetime.now().year))
            month = int(request.query_params.get('month', datetime.now().month))
            
            logger.info(f"Fetching availability for {year}-{month}")

            # Get doctor's availability for the month - ADD is_deleted=False here
            availability = DoctorAvailability.objects.filter(
                doctor=request.user.doctor_profile,
                date__year=year,
                date__month=month,
                is_deleted=False  # Only get non-deleted slots
            )
            
            logger.info(f"Found {availability.count()} availability slots")

            # Get booked appointments
            appointments = Appointment.objects.filter(
                doctor=request.user.doctor_profile,
                appointment_datetime__year=year,
                appointment_datetime__month=month
            )
            
            logger.info(f"Found {appointments.count()} booked appointments")

            # Format the response
            availability_data = {}
            for slot in availability:
                date_str = slot.date.isoformat()
                if date_str not in availability_data:
                    availability_data[date_str] = []

                # Check if this slot is booked
                is_booked = appointments.filter(
                    appointment_datetime__date=slot.date,
                    appointment_datetime__time=slot.start_time
                ).exists()

                availability_data[date_str].append({
                    'id': str(slot.id),
                    'startTime': slot.start_time.strftime('%H:%M'),
                    'endTime': slot.end_time.strftime('%H:%M'),
                    'clinicName': slot.clinic_name,
                    'isBooked': is_booked
                })

            logger.info(f"Returning availability data: {availability_data}")
            return Response({
                'success': True,
                'data': availability_data
            })

        except Exception as e:
            logger.error(f"Error in DoctorAvailabilityView: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            print("Received data:", request.data)  # Debug log
            
            if request.user.user_type != 'doctor':
                return Response({
                    'success': False,
                    'message': 'Only doctors can access this endpoint'
                }, status=status.HTTP_403_FORBIDDEN)

            date = request.data.get('date')
            start_time = request.data.get('startTime')
            clinic_name = request.data.get('clinicName')

            print(f"Processing: date={date}, start_time={start_time}, clinic_name={clinic_name}")  # Debug log

            if not all([date, start_time, clinic_name]):
                return Response({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Calculate end time (1 hour after start time)
                start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                end_time_obj = (datetime.combine(datetime.min, start_time_obj) + timedelta(hours=1)).time()

                # Create availability slot
                slot = DoctorAvailability.objects.create(
                    doctor=request.user.doctor_profile,
                    date=date,
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    clinic_name=clinic_name
                )

                return Response({
                    'success': True,
                    'data': {
                        'id': str(slot.id),
                        'startTime': start_time,
                        'endTime': end_time_obj.strftime('%H:%M'),
                        'clinicName': clinic_name,
                        'isBooked': False
                    }
                })

            except Exception as e:
                print(f"Error creating availability: {str(e)}")  # Debug log
                return Response({
                    'success': False,
                    'message': f'Error creating availability: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            print(f"Outer error: {str(e)}")  # Debug log
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DoctorAvailabilityDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if request.user.user_type != 'doctor':
                return Response({
                    'success': False,
                    'message': 'Only doctors can delete availability'
                }, status=status.HTTP_403_FORBIDDEN)

            slot_id = request.data.get('id')
            if not slot_id:
                return Response({
                    'success': False,
                    'message': 'Slot ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                availability = DoctorAvailability.objects.get(
                    id=slot_id,
                    doctor=request.user.doctor_profile
                )
                availability.delete()
                return Response({
                    'success': True,
                    'message': 'Availability deleted successfully'
                })
            except DoctorAvailability.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Availability not found'
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print(f"Error deleting availability: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { getDoctorAppointments, getDoctorProfile } from '@/services/api';
import { useRouter } from 'next/navigation';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import DoctorAvailability from './DoctorAvailability';
import { api } from '@/lib/api';
import { PostponeDialog } from './PostponeDialog';
import { CancelDialog } from './CancelDialog';
import { toast } from 'sonner';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

interface PatientProfile {
  id: number;
  user: User;
}

interface DoctorProfile {
  id: number;
  user: User;
  specialty: string;
}

interface Appointment {
  id: string;
  patient: PatientProfile;
  doctor: DoctorProfile;
  appointment_datetime: string;
  status: 'pending' | 'confirmed' | 'cancelled' | 'postponed';
  reason: string;
  created_at: string;
  updated_at: string;
}

interface DoctorInfo {
  first_name: string;
  last_name: string;
}

function formatDateTime(dateTimeStr: string) {
  const date = new Date(dateTimeStr);
  
  // Format date
  const formattedDate = date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  // Format time
  const formattedTime = date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });

  return {
    date: formattedDate,
    time: formattedTime
  };
}

export default function DoctorDashboard() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [doctorName, setDoctorName] = useState<DoctorInfo | null>(null);
  const router = useRouter();
  const [selectedAppointment, setSelectedAppointment] = useState<string | null>(null);
  const [isPostponeDialogOpen, setIsPostponeDialogOpen] = useState(false);
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.log('No token found, redirecting to login');
      router.push('/login');
      return;
    }

    const fetchAppointments = async () => {
      try {
        console.log('Fetching doctor appointments...');
        const data = await api.appointments.getDoctorAppointments();
        console.log('Raw API response:', data);
        
        if (!Array.isArray(data)) {
          console.error('Unexpected response format:', data);
          throw new Error('Invalid response format');
        }
        
        if (data.length > 0) {
          console.log('First appointment:', data[0]);
          setDoctorName({
            first_name: data[0].doctor.user.first_name,
            last_name: data[0].doctor.user.last_name
          });
        }
        
        setAppointments(data);
        setError(null);
      } catch (error) {
        console.error('Error fetching appointments:', error);
        setError(error instanceof Error ? error.message : 'Failed to load appointments');
      } finally {
        setLoading(false);
      }
    };

    fetchAppointments();
  }, [router]);

  const handlePostpone = async (datetime: string, reason: string) => {
    try {
      if (!selectedAppointment) return;
      
      await api.appointments.postponeAppointment(parseInt(selectedAppointment), {
        appointment_datetime: datetime,
        postpone_reason: reason
      });
      
      toast.success('Appointment postponed successfully');
      setIsPostponeDialogOpen(false);
      fetchAppointments();
    } catch (error) {
      console.error('Error postponing appointment:', error);
      toast.error('Failed to postpone appointment');
    }
  };

  const handleCancel = async (reason: string) => {
    try {
      if (!selectedAppointment) return;
      
      await api.appointments.cancelAppointment(parseInt(selectedAppointment), {
        cancellation_message: reason
      });
      
      toast.success('Appointment cancelled successfully');
      setIsCancelDialogOpen(false);
      fetchAppointments();
    } catch (error) {
      console.error('Error cancelling appointment:', error);
      toast.error('Failed to cancel appointment');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading appointments...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <p className="text-red-500 mb-4">Error: {error}</p>
        <Button onClick={() => window.location.reload()}>Try Again</Button>
      </div>
    );
  }

  console.log('Current appointments state:', appointments);
  if (appointments.length > 0) {
    console.log('First appointment structure:', JSON.stringify(appointments[0], null, 2));
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <Tabs defaultValue="appointments">
        <TabsList>
          <TabsTrigger value="appointments">Appointments</TabsTrigger>
          <TabsTrigger value="availability">My Availability</TabsTrigger>
        </TabsList>
        <TabsContent value="appointments">
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2">
              Hello, Dr. {doctorName ? `${doctorName.last_name}` : ''}
            </h1>
            <p className="text-gray-600">
              {appointments.length} upcoming appointment{appointments.length !== 1 ? 's' : ''}
            </p>
          </div>

          <div className="grid gap-6">
            <div>
              <h2 className="text-2xl font-bold mb-4">Upcoming Appointments</h2>
              <div className="space-y-4">
                {appointments.length > 0 ? (
                  appointments.map((appointment) => {
                    const { date, time } = formatDateTime(appointment.appointment_datetime);
                    return (
                      <Card key={appointment.id} className="hover:shadow-lg transition-shadow duration-200">
                        <CardContent className="p-6">
                          <div className="flex items-center gap-6">
                            {/* Date display */}
                            <div className="bg-blue-50 text-blue-600 rounded-xl p-4 text-center min-w-[100px] shadow-sm">
                              <div className="text-2xl font-bold">
                                {new Date(appointment.appointment_datetime).getDate()}
                              </div>
                              <div className="text-sm font-medium">
                                {new Date(appointment.appointment_datetime).toLocaleString("default", { month: "short" })}
                              </div>
                              <div className="text-xs mt-1 text-blue-500">
                                {new Date(appointment.appointment_datetime).toLocaleString("default", { weekday: "short" })}
                              </div>
                            </div>

                            {/* Appointment details */}
                            <div className="flex-1 space-y-2">
                              <div className="flex items-center gap-2">
                                <h4 className="text-lg font-semibold">
                                  Patient: {appointment.patient.user.first_name} {appointment.patient.user.last_name}
                                </h4>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  appointment.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                                  appointment.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                  appointment.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                                  'bg-gray-100 text-gray-700'
                                }`}>
                                  {appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
                                </span>
                              </div>
                              
                              <div className="text-sm text-gray-600 space-y-1">
                                <p className="flex items-center gap-2">
                                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                  </svg>
                                  {appointment.patient.user.email}
                                </p>
                                <p className="flex items-center gap-2">
                                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  {time}
                                </p>
                                {appointment.reason && (
                                  <p className="flex items-center gap-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    {appointment.reason}
                                  </p>
                                )}
                              </div>
                            </div>

                            {/* Action buttons */}
                            <div className="flex flex-col gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                className="w-24"
                                onClick={() => {
                                  setSelectedAppointment(appointment.id);
                                  setIsPostponeDialogOpen(true);
                                }}
                              >
                                Postpone
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="w-24 text-red-600 border-red-600 hover:bg-red-50"
                                onClick={() => {
                                  setSelectedAppointment(appointment.id);
                                  setIsCancelDialogOpen(true);
                                }}
                              >
                                Cancel
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })
                ) : (
                  <div className="text-center py-8 bg-gray-50 rounded-lg">
                    <p className="text-gray-500">No upcoming appointments</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </TabsContent>
        <TabsContent value="availability">
          <DoctorAvailability />
        </TabsContent>
      </Tabs>

      <PostponeDialog
        isOpen={isPostponeDialogOpen}
        onClose={() => setIsPostponeDialogOpen(false)}
        onConfirm={handlePostpone}
        appointmentId={selectedAppointment || ''}
      />
      <CancelDialog
        isOpen={isCancelDialogOpen}
        onClose={() => setIsCancelDialogOpen(false)}
        onConfirm={handleCancel}
        appointmentId={selectedAppointment || ''}
      />
    </div>
  );
} 
from django.db import models

class ChatHistory(models.Model):
    user_message = models.CharField(max_length=255)
    bot_response = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'User: {self.user_message} - Bot: {self.bot_response}'

class Appointment(models.Model):
    name = models.CharField(max_length=100)  # Patient's name
    doctor_name = models.CharField(max_length=100, default='Unknown')  # Doctor's name with default value
    department = models.CharField(max_length=100, default='General')  # Department with default value
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    token_number = models.IntegerField(default=0)  # New field for token number

    def __str__(self):
        return f'{self.name} - {self.doctor_name} - {self.appointment_date} at {self.appointment_time} - Token: {self.token_number}'

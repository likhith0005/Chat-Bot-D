from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from .models import ChatHistory, Appointment
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer, ChatterBotCorpusTrainer
import datetime

# Initialize ChatBot
bot = ChatBot(
    'chatbot',
    read_only=False,
    logic_adapters=[
        {
            'import_path': 'chatterbot.logic.BestMatch',
            'default_response': 'Sorry, I don\'t know what that means',
            'maximum_similarity_threshold': 0.90
        }
    ]
)

# Training data for the bot
list_to_train = [
    "Hi",
    "hi",
    "Hi, there",
    "What's your name?",
    "I'm just a chatbot",
    "What date would you like to schedule the appointment for? (YYYY-MM-DD)",
    "What time would you like to schedule the appointment for? (HH:MM)",
    "Which department do you need the appointment in? (e.g., Cardiology, Dermatology, etc.)",
    "Dr.Smith is available at the following times on {}: {}. Please confirm the time slot by typing the time (HH:MM).",
    "Appointment scheduled for {} with Dr. {} in {} on {} at {}. Your token number is {}.",
    "Your token number is {}.",
    "Sure, please provide your token number.",
]

# Train the chatbot
chatterbotCorpusTrainer = ChatterBotCorpusTrainer(bot)
chatterbotCorpusTrainer.train('chatterbot.corpus.english')

list_trainer = ListTrainer(bot)
list_trainer.train(list_to_train)

# Data to manage appointment state
appointment_state = {}

# Information about doctors and their availability
doctors_info = {
    "Cardiology": ["Dr.Smith", "Dr.Johnson"],
    "Dermatology": ["Dr.Brown", "Dr.Wilson"]
}

doctor_availability = {
    "Dr.Smith": ["09:00", "10:00", "14:00"],
    "Dr.Johnson": ["11:00", "13:00", "15:00"],
    "Dr.Brown": ["10:00", "12:00", "16:00"],
    "Dr.Wilson": ["09:30", "11:30", "13:30"]
}

def index(request):
    history = ChatHistory.objects.all().order_by('-timestamp')
    return render(request, 'blog/index.html', {'history': history})

def getResponse(request):
    userMessage = request.GET.get('userMessage')
    user_session_id = request.session.session_key

    if not request.session.exists(user_session_id):
        request.session.create()

    if user_session_id not in appointment_state:
        appointment_state[user_session_id] = {
            'stage': 'initial',
            'data': {}
        }

    state = appointment_state[user_session_id]

    if userMessage.lower() in ["exit", "quit", "bye"]:
        del appointment_state[user_session_id]
        chatResponse = "Goodbye!"
    elif state['stage'] == 'initial':
        if "appointment" in userMessage.lower():
            state['stage'] = 'name'
            chatResponse = "Sure, I can help with that. What is your name?"
        else:
            chatResponse = str(bot.get_response(userMessage))
    elif state['stage'] == 'name':
        state['data']['name'] = userMessage
        state['stage'] = 'date'
        chatResponse = "What date would you like to schedule the appointment for? (YYYY-MM-DD)"
    elif state['stage'] == 'date':
        try:
            date = datetime.datetime.strptime(userMessage, "%Y-%m-%d").date()
            state['data']['date'] = date
            state['stage'] = 'time'
            chatResponse = "What time would you like to schedule the appointment for? (HH:MM)"
        except ValueError:
            chatResponse = "Invalid date format. Please enter the date in YYYY-MM-DD format."
    elif state['stage'] == 'time':
        try:
            time = datetime.datetime.strptime(userMessage, "%H:%M").time()
            state['data']['time'] = time
            state['stage'] = 'department'
            chatResponse = "Which department do you need the appointment in? (e.g., Cardiology, Dermatology, etc.)"
        except ValueError:
            chatResponse = "Invalid time format. Please enter the time in HH:MM format."
    elif state['stage'] == 'department':
        if userMessage in doctors_info:
            state['data']['department'] = userMessage
            chatResponse = "Here are the available doctors in {}: {}. Please enter the doctor's name.".format(
                userMessage, ",".join(doctors_info[userMessage]))
            state['stage'] = 'doctor'
        else:
            chatResponse = "Sorry, we don't have information on that department. Please enter a valid department."
    elif state['stage'] == 'doctor':
        if userMessage in doctor_availability:
            state['data']['doctor'] = userMessage
            available_times = doctor_availability[userMessage]
            chatResponse = "{} is available at the following times on {}: {}. Please confirm the time slot by typing the time (HH:MM).".format(
                userMessage, state['data']['date'], ", ".join(available_times))
            state['stage'] = 'confirm_time'
        else:
            chatResponse = "Sorry, we don't have information on that doctor. Please enter a valid doctor."
    elif state['stage'] == 'confirm_time':
        if userMessage in doctor_availability[state['data']['doctor']]:
            state['data']['confirmed_time'] = userMessage
            token_number = generate_token_number()
            Appointment.objects.create(
                name=state['data']['name'],
                doctor_name=state['data']['doctor'],
                department=state['data']['department'],
                appointment_date=state['data']['date'],
                appointment_time=datetime.datetime.strptime(userMessage, "%H:%M").time(),
                token_number=token_number
            )
            chatResponse = "Appointment scheduled for {} with {} in {} on {} at {}. Your token number is {}.".format(
                state['data']['name'], state['data']['doctor'], state['data']['department'], state['data']['date'], userMessage, token_number)
            state['stage'] = 'token_generated'
        else:
            chatResponse = "Sorry, that time slot is not available. Please choose from the available times: {}.".format(
                ", ".join(doctor_availability[state['data']['doctor']]))
    elif userMessage.lower() == "what is my token number?":
        if 'token_number' in state['data']:
            chatResponse = "Your token number is {}.".format(state['data']['token_number'])
        else:
            chatResponse = "You haven't generated a token number yet. Please complete scheduling your appointment first."
    elif userMessage.isdigit():
        token_number = int(userMessage)
        try:
            appointment = Appointment.objects.get(token_number=token_number)
            chatResponse = "Your appointment details:\n\nPatient: {}\nDoctor: {}\nDepartment: {}\nDate: {}\nTime: {}".format(
                appointment.name, appointment.doctor_name, appointment.department, appointment.appointment_date, appointment.appointment_time)
        except Appointment.DoesNotExist:
            chatResponse = "Invalid token number. Please enter a valid token number."
    else:
        chatResponse = str(bot.get_response(userMessage))

    ChatHistory.objects.create(user_message=userMessage, bot_response=chatResponse)
    return HttpResponse(chatResponse)

def chat_history(request):
    history_entries = ChatHistory.objects.all().order_by('-timestamp')
    return render(request, 'blog/chat_history.html', {'history_entries': history_entries})

def specific(request):
    return HttpResponse("This is the specific view.")

def generate_token_number():
    import random
    return random.randint(1000, 9999)

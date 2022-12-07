import keyboard
import os
import re
import datetime
import time
import json
import openai
import azure.cognitiveservices.speech as speechsdk
from pprint import pformat
from dotenv import load_dotenv
from playsound import playsound

# loads env variables file
load_dotenv()

### AUTH KEYS ###

AZURE_SPEECH_KEY = os.getenv("AZURE") #AZURE
OAI_API_KEY = os.getenv("YOUR_API_KEY") #OPENAI
openai.api_key=OAI_API_KEY #OPEN AI INIT

# configs tts
speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region="eastus")

## STT LANGUAGES ##

speech_config.speech_recognition_language="en-US"

#speech_config.speech_recognition_language="es-US"
#speech_config.speech_recognition_language="es-MX"
#speech_config.speech_recognition_language="es-PR"
#speech_config.speech_recognition_language="es-DO"
#speech_config.speech_recognition_language="es-SV"
#speech_config.speech_recognition_language="es-CU"

#speech_config.speech_recognition_language="yue-CN"
#speech_config.speech_recognition_language="zh-CN"

#speech_config.speech_recognition_language="vi-VN"

#speech_config.speech_recognition_language="ru-RU"

#speech_config.speech_recognition_language="ar-EG"
#speech_config.speech_recognition_language="ar-SY"
#speech_config.speech_recognition_language="ar-MA"

#speech_config.speech_recognition_language="fr-FR"

#speech_config.speech_recognition_language="km-KH"

#speech_config.speech_recognition_language="it-IT"

#speech_config.speech_recognition_language="fil-PH"

#speech_config.speech_recognition_language="ja-JP"

## TTS LANGUAGES ##
# other than Aria, style compatible (-empathetic) with Davis, Guy, Jane, Jason, Jenny, Nancy, Tony

# ENGLISH #
#speech_config.speech_synthesis_voice_name='en-US-NancyNeural'
#speech_config.speech_synthesis_voice_name='en-US-JennyNeural'
speech_config.speech_synthesis_voice_name='en-US-AriaNeural'
#speech_config.speech_synthesis_voice_name='en-US-JennyMultilingualNeural'

# SPANISH #
#speech_config.speech_synthesis_voice_name='es-US-PalomaNeural' # united states
#speech_config.speech_synthesis_voice_name='es-MX-CarlotaNeural' # mexican
#speech_config.speech_synthesis_voice_name='es-PR-KarinaNeural' # puerto rican
#speech_config.speech_synthesis_voice_name='es-DO-RamonaNeural' # dominican
#speech_config.speech_synthesis_voice_name='es-SV-LorenaNeural' # salvadorean
#speech_config.speech_synthesis_voice_name='es-CU-BelkysNeural' # cuban

# CHINESE #
#speech_config.speech_synthesis_voice_name='yue-CN-XiaoMinNeural' # cantonese
#speech_config.speech_synthesis_voice_name='zh-CN-XiaochenNeural' # mandarin

# VIETNAMESE #
#speech_config.speech_synthesis_voice_name='vi-VN-HoaiMyNeural'

# RUSSIAN #
#speech_config.speech_synthesis_voice_name='ru-RU-DariyaNeural'

# ARABIC #
#speech_config.speech_synthesis_voice_name='ar-EG-SalmaNeural' # egyptian
#speech_config.speech_synthesis_voice_name='ar-SY-AmanyNeural' # syrian
#speech_config.speech_synthesis_voice_name='ar-MA-MounaNeural' # moroccan

# FRENCH #
#speech_config.speech_synthesis_voice_name='fr-FR-BrigitteNeural'

# KHMER #
#speech_config.speech_synthesis_voice_name='km-KH-SreymomNeural'

# ITALIAN #
#speech_config.speech_synthesis_voice_name='it-IT-ElsaNeural'

# TAGALOG #
#speech_config.speech_synthesis_voice_name='fil-PH-BlessicaNeural'

# JAPANESE #
#speech_config.speech_synthesis_voice_name='ja-JP-MayuNeural'

# sets voice
voice = speech_config.speech_synthesis_voice_name

# sets tts sample rate
speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Raw48Khz16BitMonoPcm)

stt_config = speechsdk.audio.AudioConfig(use_default_microphone=True) # microphone device stt
tts_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True) # speaker device tts

speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=stt_config) # inits stt
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=tts_config) # inits tts

style = "hopeful" # ssml style for voice
rate = "1.25" # speaking rate/speed
# sets up identifiers for conversation
bot = "Iva"
patient = "Bash Gutierrez"
# chart json
chart_json = {}
time_current = ""
primary_language = ""
### SETUP VARIABLES ###
context = "" # concatenates message history for re-insertion with every prompt
messages = [] # stores separate messages in list to be concatenated
silence_count = 0 # counts number of no prompt
current_requests = [] # stores recognized commands
command_prompt = "\n\n----------------COMMANDS-------------------\n\n[BED ASSIST: (DETAILS TO REPLACE)]\n[BATHROOM ASSIST: (DETAILS TO REPLACE)]\n[DRESS ASSIST: (DETAILS TO REPLACE)]\n[PAIN REQUEST: (DETAILS TO REPLACE)]\n[FOOD REQUEST: (DETAILS TO REPLACE)]\n[FLUID REQUEST: (DETAILS TO REPLACE)]\n[NURSE CALL: (DETAILS TO REPLACE)]\n\n----------------START OF CHAT-------------------\n"

def get_chart():
    
    global chart_json
    global time_current
    global primary_language
    
    # Open the JSON file
    with open('patient.json') as json_file:
        
        # Load the data from the JSON file
        chart_json = json.load(json_file)
    
    chart_json["CHART"]["LOCATION"]["datetime current"] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    
    #chart_json = chart_json["CHART"]
    
    #print(chart_json)
    
    primary_language = chart_json["CHART"]["DEMOGRAPHICS"]["primary language"]
    time_current = chart_json["CHART"]["LOCATION"]["datetime current"]
    print(time_current, primary_language)

    patient_formatted = pformat(
        chart_json,
        indent=0,
        width=80,
        compact=False,
    )

    chars_to_remove = ["'", "{", "}", "[", "]"]
    for char in chars_to_remove:
        patient_formatted = patient_formatted.replace(char, "")
        
    return patient_formatted

chart = get_chart()

def concatenate_context():
    
    global messages
    global context
    
    if len(messages) == 3:
        messages.pop()
        
    #print(len(messages))
        
    for message in messages:
        context += message

# inputs and reads patient prompt
# responds with given style from TONE_GPT3()
# returns response
def chat_gpt3(zice):
    
    global chart
    
    start_time = time.time()
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt= "You are, "+bot+", a bedside medical assistant at Trinity University Hospital for a patient named "+patient+". Speak to "+patient+" only in "+primary_language+" colloquially with patience, compassion, empathy, and assurance. The patient should be relaxed, not overwhelmed, by you and the conversations you have with them. For each request that "+patient+" needs that falls under the COMMANDS list below, alert the care team by inserting the exact command and it's details to replace between brackets within a message.\n\n----------------MEDICAL CHART JSON-------------------\n\n"+str(chart_json)+command_prompt+"\n"+context+"\n"+patient+": "+zice+"\n"+bot+":",
        #prompt= "You are, "+bot+", a clinical bedside intelligent virtual assistant (IVA) at Trinity University Hospital for a patient named "+patient+". Speak to "+patient+" only in "+language_primary+" with patience, empathy, and assurance. Keep the patient company and have conversations with them. Kindly instruct the patient to press their nurse call button on their TV remote when needed.\n\n"+chart+context+"\n"+patient+": "+zice+"\n"+bot+":",
        temperature=0.7,
        max_tokens=256,
        top_p=1.0,
        frequency_penalty=2.0,
        presence_penalty=2.0,
        stop=[patient+":", bot+":"],
        echo=False,
        stream=True,
    )
    response_time = time.time() - start_time
    
    # create variables to collect the stream of events
    collected_events = []
    completion_text = ""
    print(f"{bot}:", end="")
    
    # iterate through the stream of events
    for event in response:
        collected_events.append(event)  # save the event response
        event_text = event['choices'][0]['text']  # extract the text
        # Encode the string using the utf-8 codec
        encoded_text = event_text.encode('utf-8')
        decoded_text = encoded_text.decode('utf-8')
        completion_text += decoded_text  # append the text
        print(decoded_text, end="")  # print the delay and text
    
    # print response time
    print(f" [{response_time:.2f} S]\n")
        
    return completion_text

def parse_command(text):
    
    global current_requests
    
    # strips tts text of commands
    text_clean = re.sub(r'\[.*?\]', '', text)
    
    # compile regular expression pattern to match contents of brackets '[]'
    pattern = re.compile(r'\[(.*?)\]')
    
    # find all occurrences of pattern in string and save as list
    current_requests = pattern.findall(text)
    
    return text_clean

def run_command():
    
    global current_requests
    
    request_split = current_requests[0].split(":")
    
    command = request_split[0].upper()
    parameter = request_split[1].upper()
    
    match command:
        case "NURSE CALL":
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        case "BED ASSIST":
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        case "BATHROOM ASSIST":
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        case "DRESS ASSIST":
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        case "PAIN REQUEST":
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        case "FOOD REQUEST":
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        case "FLUID REQUEST":
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        case default:
            playsound('call.wav', False)
            print(f"\n[{time_current}] {command}: {parameter}\n")
        

# inputs response SSML from CHAT_GPT()
# streams async synthesis
def tts(ssml):
    
    global speech_synthesis_result
    
    #speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml)
    speech_synthesis_result = speech_synthesizer.speak_ssml_async(ssml).get()

def respond(prompt, response):
    
    global messages
    global silence_count
    
    response_formatted = f"{bot}:" + response

    messages.append("\n"+prompt+"\n"+response_formatted)
    
    # take out commands
    response = parse_command(response)
    
    # runs if commands are present
    if len(current_requests) == 1: run_command()

    # concats message to memory/history
    concatenate_context()

    # SSML for TTS with response and style
    xml_string = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
    xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
    <voice name="'''+voice+'''">
    <prosody rate="'''+rate+'''">
    <mstts:express-as style="'''+style+'''" styledegree="2">
    '''+ response +'''
    </mstts:express-as>
    </prosody>
    </voice>
    </speak>'''

    # synthesizes TTS with input SSML
    tts(xml_string)

    # resets silence count to 0
    silence_count = 0

# given input stt
# generates style and response from GPT-3
# synthesizes response tts
def think(inp):
    
    global silence_count
    
    # checks if there is verbal input
    if inp != "":
        
        # parses and formats patient input
        prompt = patient+": "+inp
        print("\n\n"+prompt)
        
        # gets GPT text message response completion
        response = chat_gpt3(inp)
        
        respond(prompt, response)
        
        return
    
    # assumes there is no input
    # checks if has been silent for three rounds
    elif silence_count == 2:
        
        # imitates silent input
        prompt = patient+": ..."
        print("\n\n"+prompt)
        
        # gets GPT text message response completion
        response = chat_gpt3("...")
        
        respond(prompt, response)
        
        return
            
    # increases silence count
    silence_count += 1
    
def listeningAnimation():
    
    listening = "||||||||||"
    
    for character in listening:
        time.sleep(0.005)
        print(character, end="")
    
def recognize():
    
    # gets azure stt
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    #speech_recognizer.start_continuous_recognition_async()
    
    return speech_recognition_result
    
def listen():
    
    # listens for speech
    while True:
        
        try:

            playsound('start.mp3', False)
            
            listeningAnimation()
            
            speech_recognition_result = recognize()
            
            playsound('stop.mp3', False)

            # gets tts from azure stt
            speech_recognizer.recognized.connect(think(speech_recognition_result.text))

            #message = input(patient + ": ")
            #think(message)
        
        except SystemError:
            print("keystroke exit")
        
def wait_for_key(key):
    
    while True:  # making a loop
        if keyboard.is_pressed(key):  # if key is pressed
            break  # finishing the loop

print("\nVIA-Bedside\n\nWait for the |||||||||| command and sound cue before speaking.\n\nPress the space key to continue...\n")

wait_for_key('space')

listen()
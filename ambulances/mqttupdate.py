import atexit, sys, os, time

from django.utils.six import BytesIO
from django.core.management.base import OutputWrapper
from django.core.management.color import color_style, no_style

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings

from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from .mqttclient import BaseClient, MQTTException
from .models import Ambulance, Equipment, HospitalEquipment, Hospital
from .serializers import AmbulanceSerializer, HospitalSerializer, \
    HospitalEquipmentSerializer, EquipmentSerializer, \
    ExtendedProfileSerializer

# UpdateClient class

class UpdateClient(BaseClient):

    def publish(self, topic, message, *vargs, **kwargs):
        self.client.publish(topic, message, *vargs, **kwargs)

    def update_topic(self, topic, serializer, qos=0, retain=False):
        # Publish to topic
        self.publish(topic,
                     JSONRenderer().render(serializer.data),
                     qos=qos,
                     retain=retain)
        
    def remove_topic(self, topic, serializer, qos=0):
        # Publish null to retained topic
        self.publish(topic,
                     null,
                     qos=qos,
                     retain=True)

    def update_profile(self, obj, qos=2, retain=True):
        self.update_topic('user/{}/profile'.format(obj.user.username),
                            ExtendedProfileSerializer(obj),
                            qos=qos,
                            retain=retain)
        
    def update_ambulance(self, obj, qos=2, retain=True):
        self.update_topic('ambulance/{}/data'.format(obj.id),
                            AmbulanceSerializer(obj),
                            qos=qos,
                            retain=retain)

    def remove_ambulance(self, obj):
        self.remove_topic('ambulance/{}/data'.format(obj.id))
        
    def update_hospital(self, obj, qos=2, retain=True):
        self.update_topic('hospital/{}/data'.format(obj.id),
                            HospitalSerializer(obj),
                            qos=qos,
                            retain=retain)

    def remove_hospital(self, obj):
        self.remove_topic('hospital/{}/data'.format(obj.id))
        self.remove_topic('hospital/{}/metadata'.format(obj.id))
        
    def update_hospital_metadata(self, hospital, qos=2, retain=True):
        hospital_equipment = hospital.hospitalequipment_set.values('equipment')
        equipment = Equipment.objects.filter(id__in=hospital_equipment)
        self.update_topic('hospital/{}/metadata'.format(hospital.id),
                            EquipmentSerializer(equipment, many=True),
                            qos=qos,
                            retain=retain)

    def update_hospital_equipment(self, obj, qos=2, retain=True):
        self.update_topic('hospital/{}/equipment/{}/data'.format(obj.hospital.id,
                                                                 obj.equipment.name),
                            HospitalEquipmentSerializer(obj),
                            qos=qos,
                            retain=retain)
        
    def remove_hospital_equipment(self, obj):
        self.remove_topic('hospital/{}/equipment/{}/data'.format(obj.hospital.id,
                                                                   obj.equipment.name))

import threading
        
class UpdateClientThread(threading.Thread):

    def __init__(self):

        super().__init__()

        self.client = None

    def run(self):
        
        # Start client
        stdout = OutputWrapper(sys.stdout)
        style = color_style()

        # Instantiate broker
        broker = {
            'HOST': 'localhost',
            'PORT': 1883,
            'KEEPALIVE': 60,
            'CLEAN_SESSION': True
        }

        broker.update(settings.MQTT)
        broker['CLIENT_ID'] = 'signals_' + str(os.getpid())

        connected = False
        attempts = 0
        while not connected:
            
            try:

                # try to connect
                print('Connecting to MQTT brocker...')
                self.client = UpdateClient(broker, stdout, style, 0)
                connected = self.client.connected
        
            except MQTTException as e:
                pass

            except Exception as e:
                raise e
            
            if attempts < 10:
                attempts += 1
                print('Could not connect to MQTT brocker. Retrying...')
                time.sleep(1)
            else:
                raise MQTTException('Failed to connect', -1)
                
        # start client on its own thread
        self.client.loop_start()

    def disconnect(self):

        if self.client:
            self.client.disconnect()

client = UpdateClientThread()
client.start()
            
# register atexit handler to make sure it disconnects at exit
atexit.register(client.disconnect)

# register signals

# Ambulance signals

@receiver(post_save, sender=Ambulance)
def mqtt_update_ambulance(sender, **kwargs):
    client.client.update_ambulance(kwargs['instance'])

@receiver(pre_delete, sender=Ambulance)
def mqtt_remove_ambulance(sender, **kwargs):
    client.client.remove_ambulance(kwargs['instance'])

# Hospital signals
    
@receiver(post_save, sender=Hospital)
def mqtt_update_hospital(sender, **kwargs):
    client.client.update_hospital(kwargs['instance'])
    
@receiver(pre_delete, sender=Hospital)
def mqtt_remove_hospital(sender, **kwargs):
    client.client.remove_hospital(kwargs['instance'])

# HospitalEquipment signals

@receiver(post_save, sender=HospitalEquipment)
def mqtt_update_hospital_equipment(sender, **kwargs):
    created = kwargs['created']
    obj = kwargs['instance']
    client.client.update_hospital_equipment(obj)

    # update hospital metadata
    if created:
        client.client.update_hospital_metadata(Hospital.objects.get(id=obj.hospital.id))

@receiver(pre_delete, sender=HospitalEquipment)
def mqtt_remove_hospital_equipment(sender, **kwargs):
    obj = kwargs['instance']
    client.client.remove_hospital_equipment(obj)

    # update hospital metadata
    client.client.update_hospital_metadata(obj.hospital.id)

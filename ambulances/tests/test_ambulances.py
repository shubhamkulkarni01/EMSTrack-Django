from django.test import TestCase, RequestFactory

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from django.contrib.gis.geos import Point
from django.utils import timezone

from rest_framework import serializers, test

from ambulances.models import Ambulance, \
    AmbulanceStatus, AmbulanceCapability, \
    AmbulancePermission, HospitalPermission, \
    Hospital, \
    Equipment, HospitalEquipment, EquipmentType

from ambulances.serializers import ProfileSerializer, \
    AmbulanceSerializer, ExtendedProfileSerializer, \
    HospitalSerializer, HospitalEquipmentSerializer, \
    EquipmentSerializer
#    AmbulanceCapabilitySerializer, AmbulanceSerializer, \
#    UserLocationSerializer

import collections

from django.utils.six import BytesIO
from rest_framework.parsers import JSONParser
import json

from django.test import Client

from ambulances.viewsets import AmbulanceViewSet

def date2iso(date):
    if date is not None:
        return date.isoformat().replace('+00:00','Z')
    return date

def point2str(point):
    #return 'SRID=4326;' + str(point)
    if point is not None:
        return str(point)
    return point

class TestSetup(TestCase):

    @classmethod
    def setUpTestData(cls):

        # Add users
        cls.u1 = User.objects.create_user(
            username='admin',
            email='admin@user.com',
            password='admin',
            is_superuser=True)
        
        cls.u2 = User.objects.create_user(
            username='testuser1',
            email='test1@user.com',
            password='top_secret')
        
        cls.u3 = User.objects.create_user(
            username='testuser2',
            email='test2@user.com',
            password='very_secret')
        
        # Add ambulances
        cls.a1 = Ambulance.objects.create(
            identifier='BC-179',
            comment='Maintenance due',
            capability=AmbulanceCapability.B.name,
            updated_by=cls.u1)
        
        cls.a2 = Ambulance.objects.create(
            identifier='BC-180',
            comment='Need painting',
            capability=AmbulanceCapability.A.name,
            updated_by=cls.u1)

        cls.a3 = Ambulance.objects.create(
            identifier='BC-181',
            comment='Engine overhaul',
            capability=AmbulanceCapability.R.name,
            updated_by=cls.u1)
        
        # Add hospitals
        cls.h1 = Hospital.objects.create(
            name='Hospital General',
            address="Don't know",
            updated_by=cls.u1)
        
        cls.h2 = Hospital.objects.create(
            name='Hospital CruzRoja',
            address='Forgot',
            updated_by=cls.u1)

        cls.h3 = Hospital.objects.create(
            name='Hospital Nuevo',
            address='Not built yet',
            updated_by=cls.u1)

        # add equipment
        cls.e1 = Equipment.objects.create(
            name='X-ray',
            etype=EquipmentType.B.name)

        cls.e2 = Equipment.objects.create(
            name='Beds',
            etype=EquipmentType.I.name)
        
        cls.e3 = Equipment.objects.create(
            name='MRI - Ressonance',     # name with space!
            etype=EquipmentType.B.name,
            toggleable=True)

        # add hospital equipment
        cls.he1 = HospitalEquipment.objects.create(
            hospital=cls.h1,
            equipment=cls.e1,
            value='True',
            updated_by=cls.u1)
        
        cls.he2 = HospitalEquipment.objects.create(
            hospital=cls.h1,
            equipment=cls.e2,
            value='45',
            updated_by=cls.u1)

        cls.he3 = HospitalEquipment.objects.create(
            hospital=cls.h2,
            equipment=cls.e1,
            value='False',
            updated_by=cls.u1)
        
        cls.he4 = HospitalEquipment.objects.create(
            hospital=cls.h2,
            equipment=cls.e3,
            value='True',
            updated_by=cls.u1)
        
        cls.he5 = HospitalEquipment.objects.create(
            hospital=cls.h3,
            equipment=cls.e1,
            value='True',
            updated_by=cls.u1)
        
        # add hospitals to users
        cls.u1.profile.hospitals.add(
            HospitalPermission.objects.create(hospital=cls.h1,
                                              can_write=True),
            HospitalPermission.objects.create(hospital=cls.h3)
        )
        
        cls.u2.profile.hospitals.add(
            HospitalPermission.objects.create(hospital=cls.h1),
            HospitalPermission.objects.create(hospital=cls.h2,
                                              can_write=True)
        )

        # u3 has no hospitals 
        
        # add ambulances to users
        cls.u1.profile.ambulances.add(
            AmbulancePermission.objects.create(ambulance=cls.a2,
                                               can_write=True)
        )
        
        # u2 has no ambulances
        
        cls.u3.profile.ambulances.add(
            AmbulancePermission.objects.create(ambulance=cls.a1,
                                               can_read=False),
            AmbulancePermission.objects.create(ambulance=cls.a3,
                                               can_write=True)
        )

        #print('u1: {}\n{}'.format(cls.u1, cls.u1.profile))
        #print('u2: {}\n{}'.format(cls.u2, cls.u2.profile))
        #print('u3: {}\n{}'.format(cls.u3, cls.u3.profile))

class TestProfile(TestSetup):

    def test_profile_serializer(self):

        # test ProfileSerializer
        for u in (self.u1, self.u2, self.u3):
            serializer = ProfileSerializer(u.profile)
            result = {
                'ambulances': [
                    {
                        'ambulance_id': e.ambulance.pk,
                        'ambulance_identifier': e.ambulance.identifier,
                        'can_read': e.can_read,
                        'can_write': e.can_write
                    }
                    for e in u.profile.ambulances.all()
                ],
                'hospitals': [
                    {
                        'hospital_id': e.hospital.pk,
                        'hospital_name': e.hospital.name,
                        'can_read': e.can_read,
                        'can_write': e.can_write
                    }
                    for e in u.profile.hospitals.all()
                ]
            }
            self.assertDictEqual(serializer.data, result)

    def test_extended_profile_serializer(self):

        self.maxDiff = None
        
        # test ProfileSerializer

        # regular users is just like ProfileSerializer
        for u in (self.u2, self.u3):
            serializer = ExtendedProfileSerializer(u.profile)
            result = {
                'ambulances': [
                    {
                        'ambulance_id': e.ambulance.pk,
                        'ambulance_identifier': e.ambulance.identifier,
                        'can_read': e.can_read,
                        'can_write': e.can_write
                    }
                    for e in u.profile.ambulances.all()
                ],
                'hospitals': [
                    {
                        'hospital_id': e.hospital.pk,
                        'hospital_name': e.hospital.name,
                        'can_read': e.can_read,
                        'can_write': e.can_write
                    }
                    for e in u.profile.hospitals.all()
                ]
            }
            self.assertDictEqual(serializer.data, result)

        # super will see all ambulances and hospitals
        u = self.u1
        serializer = ExtendedProfileSerializer(u.profile)
        result = {
            'ambulances': [
                {
                    'ambulance_id': e.pk,
                    'ambulance_identifier': e.identifier,
                    'can_read': True,
                    'can_write': True
                }
                for e in Ambulance.objects.all()
            ],
            'hospitals': [
                {
                    'hospital_id': e.pk,
                    'hospital_name': e.name,
                    'can_read': True,
                    'can_write': True
                }
                for e in Hospital.objects.all()
            ]
        }
        self.assertDictEqual(serializer.data, result)
            

    def test_profile_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve own
        response = client.get('/ambulances/api/profile/{}/'.format(str(self.u1.username)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = ExtendedProfileSerializer(self.u1.profile).data
        self.assertDictEqual(result, answer)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/profile/{}/'.format(str(self.u2.username)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = ExtendedProfileSerializer(self.u2.profile).data
        self.assertDictEqual(result, answer)

        # retrieve someone else's
        response = client.get('/ambulances/api/profile/{}/'.format(str(self.u3.username)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = ExtendedProfileSerializer(self.u3.profile).data
        self.assertDictEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
        
        # retrieve own
        response = client.get('/ambulances/api/profile/{}/'.format(str(self.u2.username)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = ExtendedProfileSerializer(self.u2.profile).data
        self.assertDictEqual(result, answer)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/profile/{}/'.format(str(self.u1.username)),
                              follow=True)
        self.assertEqual(response.status_code, 403)
        
        response = client.get('/ambulances/api/profile/{}/'.format(str(self.u3.username)),
                              follow=True)
        self.assertEqual(response.status_code, 403)
        
        # logout
        client.logout()

class TestAmbulance1(TestSetup):

    def test_ambulance_serializer(self):

        # test AmbulanceSerializer
        for a in (self.a1, self.a2, self.a3):
            serializer = AmbulanceSerializer(a)
            result = {
                'id': a.id,
                'identifier': a.identifier,
                'comment': a.comment,
                'capability': a.capability,
                'status': AmbulanceStatus.UK.name,
                'orientation': None,
                'location': None,
                'location_timestamp': None,
                'updated_by': a.updated_by.id,
                'updated_on': date2iso(a.updated_on)
            }
            self.assertDictEqual(serializer.data, result)

    def test_ambulance_get_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve any ambulance
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a1.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any ambulance
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a2.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any ambulance
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        self.assertDictEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve own
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # can't read
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
        
        # retrieve someone else's
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()
        
    def test_ambulance_get_list_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve ambulances
        response = client.get('/ambulances/api/ambulance/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [AmbulanceSerializer(self.a1).data,
                  AmbulanceSerializer(self.a2).data,
                  AmbulanceSerializer(self.a3).data]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve ambulances
        response = client.get('/ambulances/api/ambulance/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = []
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()
        
        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve ambulances
        response = client.get('/ambulances/api/ambulance/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [ # AmbulanceSerializer(self.a1).data, # can't read
                  AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()

class TestAmbulance2(TestSetup):
    
    def test_ambulance_update_serializer(self):
        
        # superuser first
        
        # Update ambulance status
        a = self.a1
        user = self.u1
        status = AmbulanceStatus.AH.name
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial="True")
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': status,
            'orientation': None,
            'location': point2str(a.location),
            'location_timestamp': date2iso(a.location_timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)
        
        # Update ambulance location
        location_timestamp = timezone.now()
        location = Point(-2,7)
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location,
                                             'location_timestamp': location_timestamp,
                                         }, partial="True")
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': a.status,
            'orientation': None,
            'location': point2str(location),
            'location_timestamp': date2iso(location_timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)

        # error update location with timestamp
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location,
                                         }, partial="True")
        self.assertEqual(serializer.is_valid(), False)

        # error update timestamp without location
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location_timestamp': location_timestamp,
                                         }, partial="True")
        self.assertEqual(serializer.is_valid(), False)
        
        # regular authorized user
        
        # Update ambulance status
        a = self.a3
        user = self.u3
        status = AmbulanceStatus.AH.name
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial="True")
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': status,
            'orientation': None,
            'location': point2str(a.location),
            'location_timestamp': date2iso(a.location_timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)
        
        # Update ambulance location
        location_timestamp = timezone.now()
        location = Point(-2,7)
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location,
                                             'location_timestamp': location_timestamp
                                         }, partial="True")
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': a.status,
            'orientation': None,
            'location': point2str(location),
            'location_timestamp': date2iso(location_timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)

        # error update location with timestamp
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location
                                         }, partial="True")
        self.assertEqual(serializer.is_valid(), False)

        # error update timestamp without location
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location_timestamp': location_timestamp,
                                         }, partial="True")
        self.assertEqual(serializer.is_valid(), False)
        
    def test_ambulance_patch_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve ambulance
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(self.a1).data
        self.assertDictEqual(result, answer)

        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a1.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve new ambulance status
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)
        
        # set status location
        location_timestamp = timezone.now()
        location = Point(-2,7)
        
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'location': str(location),
                                    'location_timestamp': date2iso(location_timestamp),
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a1.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve new ambulance location
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)
        self.assertEqual(result['location'], 'SRID=4326;' + str(location))
        self.assertEqual(result['location_timestamp'], date2iso(location_timestamp))
        
        # set wrong attribute
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': 'will fail'
                                })
        )
        self.assertEqual(response.status_code, 400)
        
        # set wrong ambulance id
        response = client.patch('/ambulances/api/ambulance/100/',
                                data = json.dumps({
                                    'status': status
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve ambulance
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(self.a3).data
        self.assertDictEqual(result, answer)

        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve new ambulance status
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)
        
        # set status location
        location_timestamp = timezone.now()
        location = Point(-2,7)
        
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'location': str(location),
                                    'location_timestamp': date2iso(location_timestamp),
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve new ambulance location
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)
        self.assertEqual(result['location'], 'SRID=4326;' + str(location))
        self.assertEqual(result['location_timestamp'], date2iso(location_timestamp))
        
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a2.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
                
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a2.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)

        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/ambulances/api/ambulance/{}/'.format(str(self.a3.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

class TestAmbulance3(TestSetup):

    def test_ambulance_create_serializer(self):

        serializer = AmbulanceSerializer(data={
            'identifier': 'NEW-1897',
            'capability': AmbulanceCapability.R.name,
            'comment': 'no comments'
        })
        serializer.is_valid()
        serializer.save(updated_by = self.u1)
        
        # test AmbulanceSerializer
        a = Ambulance.objects.get(identifier='NEW-1897')
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': 'NEW-1897',
            'comment': 'no comments',
            'capability': AmbulanceCapability.R.name,
            'status': AmbulanceStatus.UK.name,
            'orientation': None,
            'location': None,
            'location_timestamp': None,
            'updated_by': self.u1.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)

    def test_ambulance_post_view(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # create ambulance
        response = client.post('/ambulances/api/ambulance/',
                               {
                                   'identifier': 'NEW-1897',
                                   'capability': AmbulanceCapability.R.name,
                                   'comment': 'no comments'
                               }
        )
        self.assertEqual(response.status_code, 201)
        a = Ambulance.objects.get(identifier='NEW-1897')
        
        # retrieve ambulance
        response = client.get('/ambulances/api/ambulance/{}/'.format(str(a.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(a).data
        self.assertDictEqual(result, answer)

        # create ambulance (repeated identifier)
        response = client.post('/ambulances/api/ambulance/',
                               {
                                   'identifier': 'NEW-1897',
                                   'capability': AmbulanceCapability.R.name,
                                   'comment': 'no comments'
                               }
        )
        self.assertEqual(response.status_code, 400)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['identifier'],
                         ['ambulance with this identifier already exists.'])
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        response = client.post('/ambulances/api/ambulance/',
                               {
                                   'identifier': 'NEW-NEW-1897',
                                   'capability': AmbulanceCapability.B.name,
                                   'comment': 'more comments'
                               }
        )
        self.assertEqual(response.status_code, 403)

        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
                
        response = client.post('/ambulances/api/ambulance/',
                               {
                                   'identifier': 'NEW-NEW-1897',
                                   'capability': AmbulanceCapability.B.name,
                                   'comment': 'more comments'
                               }
        )
        self.assertEqual(response.status_code, 403)
        
        # logout
        client.logout()
        
class TestHospital1(TestSetup):

    def test_hospital_serializer(self):

        # test HospitalSerializer
        for h in (self.h1, self.h2, self.h3):
            serializer = HospitalSerializer(h)
            result = {
                'id': h.id,
                'name': h.name,
                'address': h.address,
                'location': None,
                'updated_by': h.updated_by.id,
                'updated_on': date2iso(h.updated_on)
            }
            self.assertDictEqual(serializer.data, result)

    def test_hospital_get_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve any hospital
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalSerializer(Hospital.objects.get(id=self.h1.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any hospital
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalSerializer(Hospital.objects.get(id=self.h2.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any hospital
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalSerializer(Hospital.objects.get(id=self.h3.id)).data
        self.assertDictEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
        
        # retrieve own's
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalSerializer(Hospital.objects.get(id=self.h1.id)).data
        self.assertDictEqual(result, answer)
        
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalSerializer(Hospital.objects.get(id=self.h2.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()
        
    def test_hospital_get_list_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve hospitals
        response = client.get('/ambulances/api/hospital/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [HospitalSerializer(self.h1).data,
                  HospitalSerializer(self.h2).data,
                  HospitalSerializer(self.h3).data]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve hospitals
        response = client.get('/ambulances/api/hospital/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            HospitalSerializer(Hospital.objects.get(id=self.h1.id)).data,
            HospitalSerializer(Hospital.objects.get(id=self.h2.id)).data
        ]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()
        
        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve hospitals
        response = client.get('/ambulances/api/hospital/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = []
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()

class TestHospitalEquipment(TestSetup):

    def test_hospital_equipment_serializer(self):

        # test HospitalSerializer
        for he in (self.he1, self.he2, self.he3, self.he4):
            serializer = HospitalEquipmentSerializer(he)
            result = {
                'hospital_id': he.hospital.id,
                'hospital_name': he.hospital.name,
                'equipment_id': he.equipment.id,
                'equipment_name': he.equipment.name,
                'value': he.value,
                'comment': he.comment,
                'updated_by': he.updated_by.id,
                'updated_on': date2iso(he.updated_on)
            }
            self.assertDictEqual(serializer.data, result)

    def test_hospital_equipment_get_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h1.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e1.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h1.id), str(self.e2.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e2.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h2.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e1.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h2.id), str(self.e3.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e3.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h3.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h3.id,equipment=self.e1.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve inexistent
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h3.id), str(self.e2.name)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h3.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve own hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h1.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e1.id)).data
        self.assertDictEqual(result, answer)

        # retrieve own hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h1.id), str(self.e2.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e2.id)).data
        self.assertDictEqual(result, answer)

        # retrieve own hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h2.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e1.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve own hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h2.id), str(self.e3.name)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e3.id)).data
        self.assertDictEqual(result, answer)

        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h3.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h1.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h1.id), str(self.e2.name)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h2.id), str(self.e1.name)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve someone else's
        response = client.get('/ambulances/api/hospital/{}/equipment/{}/'.format(str(self.h2.id), str(self.e3.name)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

    def test_hospital_equipment_list_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e1.id)).data,
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e2.id)).data
        ]
        
        self.assertCountEqual(result, answer)

        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e1.id)).data,
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e3.id)).data
        ]
        self.assertCountEqual(result, answer)
        
        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h3.id,equipment=self.e1.id)).data
        ]
        self.assertCountEqual(result, answer)
        
        # retrieve inexistent
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(1000),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e1.id)).data,
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h1.id,equipment=self.e2.id)).data
        ]
        
        self.assertCountEqual(result, answer)

        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e1.id)).data,
            HospitalEquipmentSerializer(HospitalEquipment.objects.get(hospital=self.h2.id,equipment=self.e3.id)).data
        ]
        self.assertCountEqual(result, answer)
        
        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
        ]
        self.assertCountEqual(result, answer)
        
        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
        ]
        self.assertCountEqual(result, answer)

        # retrieve all hospital equipment
        response = client.get('/ambulances/api/hospital/{}/equipment/'.format(str(self.h3.id)),
                              follow=True)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
        ]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()
        
    def test_hospital_equipment_metadata_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username='admin', password='admin')

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            EquipmentSerializer(Equipment.objects.get(id=self.e1.id)).data,
            EquipmentSerializer(Equipment.objects.get(id=self.e2.id)).data
            ]
        self.assertCountEqual(result, answer)

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            EquipmentSerializer(Equipment.objects.get(id=self.e1.id)).data,
            EquipmentSerializer(Equipment.objects.get(id=self.e3.id)).data
            ]
        self.assertCountEqual(result, answer)
        
        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            EquipmentSerializer(Equipment.objects.get(id=self.e1.id)).data
            ]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            EquipmentSerializer(Equipment.objects.get(id=self.e1.id)).data,
            EquipmentSerializer(Equipment.objects.get(id=self.e2.id)).data
            ]
        self.assertCountEqual(result, answer)

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [
            EquipmentSerializer(Equipment.objects.get(id=self.e1.id)).data,
            EquipmentSerializer(Equipment.objects.get(id=self.e3.id)).data
            ]
        self.assertCountEqual(result, answer)
        
        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve any hospital equipment
        response = client.get('/ambulances/api/hospital/{}/metadata/'.format(str(self.h3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()
        

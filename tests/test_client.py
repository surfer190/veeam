from unittest import TestCase
from unittest.mock import patch

import requests
import responses
from freezegun import freeze_time

from veeam.client import VeeamClient
from veeam.errors import LoginFailError, LoginFailSessionKeyError

REPO_SUMMARY_RESPONSE = {
    "Periods": [
        {
            "Name": "Scale-Out_Backup_Repository_1",
            "Capacity": 14010040700928,
            "FreeSpace": 5440467521536,
            "BackupSize": 8569573179392
        },
        {
            "Name": "TEST_PROXY_NODE1",
            "Capacity": 372152239390720,
            "FreeSpace": 257601197572096,
            "BackupSize": 114551041818624
        },
        {
            "Name": "TEST_JB1_NONGEO_Veeam_09",
            "Capacity": 9556164866048,
            "FreeSpace": 2106336800768,
            "BackupSize": 7449828065280
        }
    ],
    "CapacityPlanningReportLink": "Workspace/ViewReport.aspx?definition=62221565-102c-4ec8-851b-d61c03d972d1&ShowParams=1"
}

FAILED_JOBS_RESPONSE = {
    "Entities": {
        "BackupJobSessions": {
            "BackupJobSessions": [
                {
                    "IsRetry": False,
                    "JobUid": "urn:veeam:Job:dec7aae1-2124-43dc-a599-d6da0d724201",
                    "JobName": "Vrfpoller Servers ECS_Ter",
                    "JobType": "Backup",
                    "CreationTimeUTC": "2019-07-01T04:00:16Z",
                    "EndTimeUTC": "2019-07-01T06:26:56Z",
                    "State": "Stopped",
                    "Result": "Failed",
                    "Progress": 100,
                    "Name": "Vrfpoller Servers ECS_Ter@2019-07-01 04:00:16",
                    "UID": "urn:veeam:BackupJobSession:514a5930-5390-4811-b4a8-1d67004f39e7",
                    "Links": [
                        {
                            "Rel": "Up",
                            "Href": "http://192.168.16.21:9399/api/backupServers/62f06091-56a7-4aa3-bf4a-f2df501b8fd9",
                            "Name": "192.168.16.21",
                            "Type": "BackupServerReference"
                        }
                    ],
                    "Href": "http://192.168.16.21:9399/api/backupSessions/514a5930-5390-4811-b4a8-1d67004f39e7?format=Entity",
                    "Type": "BackupJobSession"
                }
            ]
        }
    },
    "PagingInfo": {
        "Links": [
            {
                "Rel": "First",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=result%3d%3d%22Failed%22%3bendtime%3e%222019-06-30%22&pageSize=100&page=1"
            },
            {
                "Rel": "Last",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=result%3d%3d%22Failed%22%3bendtime%3e%222019-06-30%22&pageSize=100&page=1"
            }
        ],
        "PageNum": 1,
        "PageSize": 100,
        "PagesCount": 1
    }
}

SUCCESSFUL_JOBS_RESPONSE = {
    "Entities": {
        "BackupJobSessions": {
            "BackupJobSessions": [
                {
                    "IsRetry": True,
                    "JobUid": "urn:veeam:Job:dec7aae1-2124-43dc-a599-d6da0d724201",
                    "JobName": "Vrfpoller Servers ECS_Ter",
                    "JobType": "Backup",
                    "CreationTimeUTC": "2019-07-01T06:36:58Z",
                    "EndTimeUTC": "2019-07-01T06:39:19Z",
                    "State": "Stopped",
                    "Result": "Success",
                    "Progress": 100,
                    "Name": "Vrfpoller Servers ECS_Ter@2019-07-01 06:36:58",
                    "UID": "urn:veeam:BackupJobSession:758b4561-fada-4742-ad4b-2121c341b5da",
                    "Links": [
                        {
                            "Rel": "Up",
                            "Href": "http://192.168.16.21:9399/api/backupServers/62f06091-56a7-4aa3-bf4a-f2df501b8fd9",
                            "Name": "192.168.16.21",
                            "Type": "BackupServerReference"
                        },
                        {
                            "Rel": "Up",
                            "Href": "http://192.168.16.21:9399/api/jobs/dec7aae1-2124-43dc-a599-d6da0d724201",
                            "Name": "Vrfpoller Servers ECS_Ter",
                            "Type": "JobReference"
                        },
                        {
                            "Rel": "Alternate",
                            "Href": "http://192.168.16.21:9399/api/backupSessions/758b4561-fada-4742-ad4b-2121c341b5da",
                            "Name": "Vrfpoller Servers ECS_Ter@2019-07-01 06:36:58",
                            "Type": "BackupJobSessionReference"
                        },
                        {
                            "Rel": "Down",
                            "Href": "http://192.168.16.21:9399/api/backupSessions/758b4561-fada-4742-ad4b-2121c341b5da/taskSessions",
                            "Type": "BackupTaskSessionReferenceList"
                        },
                        {
                            "Rel": "Stop",
                            "Href": "http://192.168.16.21:9399/api/backupSessions/758b4561-fada-4742-ad4b-2121c341b5da?action=stop"
                        }
                    ],
                    "Href": "http://192.168.16.21:9399/api/backupSessions/758b4561-fada-4742-ad4b-2121c341b5da?format=Entity",
                    "Type": "BackupJobSession"
                }
            ]
        }
    },
    "PagingInfo": {
        "Links": [
            {
                "Rel": "First",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=jobname%3d%3d%22Vrfpoller+Servers+ECS_Ter%22%3bresult%3d%3d%22Success%22%3bcreationtime%3e%222019-07-01T04%3a00%3a16Z%22&pageSize=100&page=1"
            },
            {
                "Rel": "Last",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=jobname%3d%3d%22Vrfpoller+Servers+ECS_Ter%22%3bresult%3d%3d%22Success%22%3bcreationtime%3e%222019-07-01T04%3a00%3a16Z%22&pageSize=100&page=1"
            }
        ],
        "PageNum": 1,
        "PageSize": 100,
        "PagesCount": 1
    }
}

EMPTY_SUCCESSFUL_JOBS_RESPONSE = {
    "Entities": {
        "BackupJobSessions": {
            "BackupJobSessions": []
        }
    },
    "PagingInfo": {
        "Links": [
            {
                "Rel": "First",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=jobname%3d%3d%22Vrfpoller+Servers+ECS_Ter%22%3bresult%3d%3d%22Success%22%3bcreationtime%3e%222019-07-02T04%3a00%3a16Z%22&pageSize=100&page=1"
            },
            {
                "Rel": "Last",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=jobname%3d%3d%22Vrfpoller+Servers+ECS_Ter%22%3bresult%3d%3d%22Success%22%3bcreationtime%3e%222019-07-02T04%3a00%3a16Z%22&pageSize=100&page=1"
            }
        ],
        "PageNum": 1,
        "PageSize": 100,
        "PagesCount": 1
    }
}

BACKUP_SESSION_RESPONSE = {
    "Entities": {
        "BackupJobSessions": {
            "BackupJobSessions": [
                {
                    "IsRetry": False,
                    "JobUid": "urn:veeam:Job:dabfecfa-4320-40c5-8d43-71b4029d99ee",
                    "JobName": "Jhb-web1",
                    "JobType": "Backup",
                    "CreationTimeUTC": "2019-07-02T01:50:05Z",
                    "EndTimeUTC": "2019-07-02T01:58:07Z",
                    "State": "Stopped",
                    "Result": "Success",
                    "Progress": 100,
                    "Name": "Jhb-web1@2019-07-02 01:50:05",
                    "UID": "urn:veeam:BackupJobSession:3d5f5b00-a91e-4b55-9417-fcd08ec1df08",
                    "Links": [
                        {
                            "Rel": "Up",
                            "Href": "http://192.168.16.21:9399/api/backupServers/62f06091-56a7-4aa3-bf4a-f2df501b8fd9",
                            "Name": "192.168.16.21",
                            "Type": "BackupServerReference"
                        },
                        {
                            "Rel": "Up",
                            "Href": "http://192.168.16.21:9399/api/jobs/dabfecfa-4320-40c5-8d43-71b4029d99ee",
                            "Name": "Jhb-web1",
                            "Type": "JobReference"
                        },
                        {
                            "Rel": "Alternate",
                            "Href": "http://192.168.16.21:9399/api/backupSessions/3d5f5b00-a91e-4b55-9417-fcd08ec1df08",
                            "Name": "Jhb-web1@2019-07-02 01:50:05",
                            "Type": "BackupJobSessionReference"
                        },
                        {
                            "Rel": "Down",
                            "Href": "http://192.168.16.21:9399/api/backupSessions/3d5f5b00-a91e-4b55-9417-fcd08ec1df08/taskSessions",
                            "Type": "BackupTaskSessionReferenceList"
                        },
                        {
                            "Rel": "Stop",
                            "Href": "http://192.168.16.21:9399/api/backupSessions/3d5f5b00-a91e-4b55-9417-fcd08ec1df08?action=stop"
                        },
                        {
                            "Rel": "Related",
                            "Href": "http://192.168.16.21:9399/api/restorePoints/2df63ff1-4e77-4f9d-96b4-d2716b7ab7eb",
                            "Name": "Jul  2 2019  1:50AM",
                            "Type": "RestorePointReference"
                        }
                    ],
                    "Href": "http://192.168.16.21:9399/api/backupSessions/3d5f5b00-a91e-4b55-9417-fcd08ec1df08?format=Entity",
                    "Type": "BackupJobSession"
                }
            ]
        }
    },
    "PagingInfo": {
        "Links": [
            {
                "Rel": "First",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=creationtime%3e%222019-07-01T09%3a33%3a51Z%22&pageSize=100&page=1"
            },
            {
                "Rel": "Last",
                "Href": "http://192.168.16.21:9399/api/query?type=BackupJobSession&format=entities&filter=creationtime%3e%222019-07-01T09%3a33%3a51Z%22&pageSize=100&page=1"
            }
        ],
        "PageNum": 1,
        "PageSize": 100,
        "PagesCount": 1
    }
}

class VeeamClientTestCase(TestCase):
    '''
    Veeam client testcase
    '''
    
    BASE_API_URL = 'http://test:3991/api'
    
    @responses.activate
    def test_session_headers_set(self):
        '''
        Ensure the session header for auth and accept is set after init
        '''
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
                status=201,
                headers={'X-RestSvcSessionId': 'MMM'}
        )
        client = VeeamClient(self.BASE_API_URL, 'username', 'pass')
        self.assertEqual(
            client.session.headers['X-RestSvcSessionId'],
            'MMM'
        )
        self.assertEqual(
            client.session.headers['Accept'],
            'application/json'
        )

    @responses.activate
    def test_failed_login(self):
        '''
        Ensure an error is raised when login fails
        '''
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'Message': 'The user name or password is incorrect'},
                status=401,
        )
        with self.assertRaises(LoginFailError):
            client = VeeamClient(self.BASE_API_URL, 'username', 'pass')

    @responses.activate
    def test_error_no_url(self):
        '''
        Ensure an error is raised when there is no url
        '''
        with self.assertRaises(TypeError):
            client = VeeamClient()

    @responses.activate
    def test_error_no_username_password_set(self):
        '''
        Ensure the session header for auth and accept is set after init
        '''
        with self.assertRaises(TypeError):
            client = VeeamClient()

    @responses.activate
    def test_get_failed_jobs(self):
        '''
        Ensure failed jobs are returned
        '''
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
                status=201,
                headers={'X-RestSvcSessionId': 'MMM'}
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/query?type=BackupJobSession&format=entities&filter=result==%22Failed%22;endtime%3E%222019-06-30%22',
            json=FAILED_JOBS_RESPONSE,
            status=200
        )
        
        client = VeeamClient(self.BASE_API_URL, 'username', 'pass')
        failed_jobs = client.get_failed_jobs()
        
        self.assertEqual(
            failed_jobs,
            FAILED_JOBS_RESPONSE['Entities']['BackupJobSessions']['BackupJobSessions']
        )

    @patch.object(VeeamClient, 'get_successful_jobs')
    @responses.activate
    def test_persistently_failed_jobs_calls_successful(self, mock_successful):
        '''
        Ensure persistently failed jobs calls the successful jobs method
        '''
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
                status=201,
                headers={'X-RestSvcSessionId': 'MMM'}
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/query?type=BackupJobSession&format=entities&filter=result==%22Failed%22;creationtime%3E%222019-06-30%22',
            json=FAILED_JOBS_RESPONSE,
            status=200
        )
        client = VeeamClient(self.BASE_API_URL, 'username', 'pass')
        persistently_failed_jobs = client.get_persistently_failed_jobs()

        job_name = FAILED_JOBS_RESPONSE['Entities']['BackupJobSessions']['BackupJobSessions'][0]['JobName']
        creationtime = FAILED_JOBS_RESPONSE['Entities']['BackupJobSessions']['BackupJobSessions'][0]['CreationTimeUTC']
        
        mock_successful.assert_called_with(job_name, creationtime)

    @freeze_time("2019-07-01 10:08:02")
    @responses.activate
    def test_repos_percentage(self):
        '''
        Ensure the free space percentage is added to the repos
        '''
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
                status=201,
                headers={'X-RestSvcSessionId': 'MMM'}
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/reports/summary/repository',
            json=REPO_SUMMARY_RESPONSE,
            status=200
        )
        client = VeeamClient(self.BASE_API_URL, 'username', 'pass')
        repos = client.get_repos()
        
        self.assertEqual(
            repos,
            [
                {
                    'Name': 'Scale-Out_Backup_Repository_1',
                    'Capacity': 14010040700928,
                    'FreeSpace': 5440467521536,
                    'BackupSize': 8569573179392,
                    'percentage_free': 38.83,
                    'message_type': 'repo',
                    'date': 'Mon Jul  1 10:08:02 2019'
                },
                {
                    'Name': 'TEST_PROXY_NODE1',
                    'Capacity': 372152239390720,
                    'FreeSpace': 257601197572096,
                    'BackupSize': 114551041818624,
                    'percentage_free': 69.22,
                    'message_type': 'repo',
                    'date': 'Mon Jul  1 10:08:02 2019'
                },
                {
                    'Name': 'TEST_JB1_NONGEO_Veeam_09',
                    'Capacity': 9556164866048,
                    'FreeSpace': 2106336800768,
                    'BackupSize': 7449828065280,
                    'percentage_free': 22.04,
                    'message_type': 'repo',
                    'date': 'Mon Jul  1 10:08:02 2019'
                }
            ]
        )

    @responses.activate
    def test_persistently_failed_jobs_returned(self):
        '''
        Ensure persistently failed jobs are returned when no successful
        '''
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
                status=201,
                headers={'X-RestSvcSessionId': 'MMM'}
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/query?type=BackupJobSession&format=entities&filter=result==%22Failed%22;creationtime%3E%222019-06-30%22',
            json=FAILED_JOBS_RESPONSE,
            status=200
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/query?type=BackupJobSession&format=entities&filter=jobname==%22Vrfpoller%20Servers%20ECS_Ter%22;(result==%22Success%22,result==%22Warning%22);creationtime%3E%222019-07-01T04:00:16Z%22',
            json=EMPTY_SUCCESSFUL_JOBS_RESPONSE,
            status=200
        )
        
        client = VeeamClient(self.BASE_API_URL, 'username', 'pass')
        persistently_failed_jobs = client.get_persistently_failed_jobs()
        
        self.assertEqual(
            persistently_failed_jobs,
            [
                {
                    'IsRetry': False, 'JobUid': 'urn:veeam:Job:dec7aae1-2124-43dc-a599-d6da0d724201', 'JobName': 'Vrfpoller Servers ECS_Ter', 'JobType': 'Backup', 'CreationTimeUTC': '2019-07-01T04:00:16Z', 'EndTimeUTC': '2019-07-01T06:26:56Z', 'State': 'Stopped', 'Result': 'Failed', 'Progress': 100, 'Name': 'Vrfpoller Servers ECS_Ter@2019-07-01 04:00:16', 'UID': 'urn:veeam:BackupJobSession:514a5930-5390-4811-b4a8-1d67004f39e7', 'Links': [{'Rel': 'Up', 'Href': 'http://192.168.16.21:9399/api/backupServers/62f06091-56a7-4aa3-bf4a-f2df501b8fd9', 'Name': '192.168.16.21', 'Type': 'BackupServerReference'}], 'Href': 'http://192.168.16.21:9399/api/backupSessions/514a5930-5390-4811-b4a8-1d67004f39e7?format=Entity', 'Type': 'BackupJobSession', 'message_type': 'job_failed'
                }
            ]
        )


    @responses.activate
    def test_persistently_failed_jobs_not_returned(self):
        '''
        Ensure persistently failed jobs are not returned when there are successful
        '''
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
                status=201,
                headers={'X-RestSvcSessionId': 'MMM'}
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/query?type=BackupJobSession&format=entities&filter=result==%22Failed%22;creationtime%3E%222019-06-30%22',
            json=FAILED_JOBS_RESPONSE,
            status=200
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/query?type=BackupJobSession&format=entities&filter=jobname==%22Vrfpoller%20Servers%20ECS_Ter%22;(result==%22Success%22,result==%22Warning%22);creationtime%3E%222019-07-01T04:00:16Z%22',
            json=SUCCESSFUL_JOBS_RESPONSE,
            status=200
        )
        
        client = VeeamClient(self.BASE_API_URL, 'username', 'pass')
        persistently_failed_jobs = client.get_persistently_failed_jobs()
        
        self.assertEqual(
            persistently_failed_jobs,
            []
        )

    @freeze_time("2019-07-01 10:08:02")
    @responses.activate
    def test_last_day_jobs(self):
        responses.add(
            responses.POST, f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
                json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
                status=201,
                headers={'X-RestSvcSessionId': 'MMM'}
        )
        responses.add(
            responses.GET,
            f'{ self.BASE_API_URL }/query?type=BackupJobSession&format=entities&filter=creationtime%3E%222019-06-30T10:08:02Z%22',
            json=BACKUP_SESSION_RESPONSE,
            status=200
        )
        client = VeeamClient(self.BASE_API_URL, 'username', 'pass')
        repos = client.get_jobs_1_day()
        
        self.assertEqual(
            len(repos),
            1
        )
        
        self.assertEqual(
            repos[0]['message_type'],
            'job'
        )

    @responses.activate
    def test_provide_own_session(self):
        '''
        Ensure a session can be provided in keyword arguments
        '''
        responses.add(
            responses.POST,
            f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
            json={'UserName': 'VEEAM\\veeam.api', 'SessionId': '2fb28f4f-46bd-4855-a757-0b8c24f9826b'},
            status=201,
            headers={'X-RestSvcSessionId': 'MMM'}
        )
        
        token = '12345'
        session = requests.Session()
        session.headers.update({'my_token': token})
        session.verify = False
        
        veeam_client = VeeamClient(self.BASE_API_URL, 'username', 'password', session=session)
        
        self.assertEqual(
            veeam_client.session.headers['my_token'],
            token
        )
        self.assertFalse(veeam_client.session.verify)

    @responses.activate
    def test_no_session_token_response(self):
        '''
        Ensure no session token response raises an error
        '''
        responses.add(
            responses.POST,
            f'{ self.BASE_API_URL }/sessionMngr/?v=v1_4',
            json={},
            status=201
        )
        
        token = '12345'
        session = requests.Session()
        session.headers.update({'my_token': token})
        session.verify = False
        
        with self.assertRaises(LoginFailSessionKeyError):
            veeam_client = VeeamClient(self.BASE_API_URL, 'username', 'password', session=session)

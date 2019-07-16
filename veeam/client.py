import datetime

import requests
from requests.auth import HTTPBasicAuth

from .errors import LoginFailError, LoginFailSessionKeyError


class VeeamClient(object):
    '''
    Client for interacting with the Veeam API
    https://helpcenter.veeam.com/backup/rest/overview.html
    '''
    
    def __init__(self, url, veeam_username, veeam_password, verify=False, session=None):
        '''
        1. Create or use the existing session
        2. Authenticate with the Veeam API
        '''
        if not session:
            session = requests.Session()
        
        self.url = url
        self.login_url = '{}/sessionMngr/?v=v1_4'.format(url)
        self.verify = verify
        self.session = session

        auth = HTTPBasicAuth(veeam_username, veeam_password)

        self.session.headers.update({'Accept': 'application/json'})

        login = self.session.post(
            self.login_url,
            auth=auth,
            verify=verify
        )
        
        if login.status_code  == 201:
            try:
                session_token = login.headers['X-RestSvcSessionId']
            except KeyError:
                raise LoginFailSessionKeyError()
        else:
            raise LoginFailError('Authentication failed')

        self.session.headers.update(
            {
                'X-RestSvcSessionId': session_token,
                'Accept': 'application/json'
            }
        )
        self.session.verify = verify

    def get_repo_summary(self):
        '''
        Get the summary of repo's
        '''
        repos = self.session.get('{}/reports/summary/repository'.format(self.url))
        repositories = repos.json()
        return repositories

    def get_jobs(self):
        '''
        Get all jobs
        '''
        jobs = self.session.get('{}/jobs'.format(self.url))
        return jobs.json()
    
    def get_backups(self):
        '''
        Get backups created on or imported to Veeam backup servers
        '''
        backups = self.session.get('{}/backups'.format(self.url))
        return backups.json()
    
    def get_backup(self, uuid):
        '''
        Get a single backup info
        
        Arguments:
            uuid {uuid}
        
        Returns:
            json (python dict) -- single backup info
        '''
        backup = self.session.get('{url}/backups/{uuid}?format=Entity'.format(
            url=self.url,
            uuid=uuid
        ))
        return backup.json()
    
    def get_restore_points(self, backup_uuid):
        restore_points = self.session.get('{url}/backups/{uuid}/restorePoints'.format(
            url=self.url,
            uuid=backup_uuid
        ))
        return restore_points.json()
    
    def get_vm_restore_points(self, restore_point_uuid):
        vm_restore_points = self.session.get('{url}/restorePoints/{uuid}/vmRestorePoints'.format(
            url=self.url,
            uuid=restore_point_uuid
        ))
        return vm_restore_points.json()

    def get_vms_processed_day(self):
        '''
        Return the number of vms process per day
        '''
        summary_vms = self.session.get(
            '{url}/reports/summary/processed_vms'.format(
                url=self.url
            )
        )
        return summary_vms.json()

    def get_summary_job_stats(self):
        '''
        Return the summary job stats
        '''
        summary_job_stats = self.session.get(
            '{url}/reports/summary/job_statistics'.format(url=self.url)
        )
        return summary_job_stats.json()

    def get_summary_vms(self):
        '''
        Return the summary vm stats
        '''
        summary_vm_stats = self.session.get(
            '{url}/reports/summary/vms_overview'.format(url=self.url)
        )
        return summary_vm_stats.json()

    def get_summary_overview(self):
        '''
        Return the summary overview stats
        '''
        summary_overview_stats = self.session.get(
            '{url}/reports/summary/overview'.format(url=self.url)
        )
        return summary_overview_stats.json()

    def get_date_yesterday(self):
        '''
        Return the date yesterday
        '''
        today = datetime.datetime.now(tz=datetime.timezone.utc)
        yesterday = today - datetime.timedelta(days=1)
        yesterday_rep = yesterday.isoformat(timespec='seconds').replace('+00:00', 'Z')
        return yesterday_rep

    def get_jobs_1_day(self):
        '''
        Get all jobs started in the last 1 day and add a type
        '''
        yesterday_rep = self.get_date_yesterday()
        job_stats = self.session.get(
            '{}/query?type=BackupJobSession&format=entities&filter=creationtime>"{}"'.format(
                self.url, yesterday_rep)
        )
        
        jobs = job_stats.json()['Entities']['BackupJobSessions']['BackupJobSessions']
        
        all_jobs = []
        
        for job in jobs:
            job['message_type'] = 'job'
            all_jobs.append(job)

        return all_jobs
    
    def get_failed_jobs(self):
        '''
        Get backup job sessions since yesterday that are failed or warning
        '''
        yesterday_rep = self.get_date_yesterday()
        job_stats = self.session.get(
            '{}/query?type=BackupJobSession&format=entities&filter=result=="Failed";creationtime>"{}"'.format(
                self.url, yesterday_rep)
        )
        jobs = job_stats.json()['Entities']['BackupJobSessions']['BackupJobSessions']

        return jobs
    
    def get_successful_jobs(self, jobname, since):
        '''
        Get all the jobs that were successful/warning for a specific job name
        starting after a specific date a specific date
        '''
        job_stats = self.session.get(
            '{}/query?type=BackupJobSession&format=entities&filter=jobname=="{}";(result=="Success",result=="Warning");creationtime>"{}"'.format(
                self.url, jobname, since)
        )
        
        jobs = job_stats.json()['Entities']['BackupJobSessions']['BackupJobSessions']

        return jobs
    
    def get_persistently_failed_jobs(self):
        '''
        Get all the failed jobs from a day and 1 hour ago
        that do not have a successful job after the fail start time
        
        1. Get failed jobs
        2. For each failed job - get successful jobs after the failed start time
        3. If no successful jobs exist - add to the report payload
        '''
        failed_jobs = self.get_failed_jobs()
        
        all_failed_jobs = []
        
        for failed_job in failed_jobs:
            successful_jobs = self.get_successful_jobs(failed_job['JobName'], failed_job['CreationTimeUTC'])
            if len(successful_jobs) < 1:
                failed_job['message_type'] = 'job_failed'
                all_failed_jobs.append(failed_job)
        
        return all_failed_jobs

    def get_repos(self):
        '''
        Get the repos for the veeam instance
        
        Add FreeSpace percentage
        '''
        repo_summary = self.get_repo_summary()
        
        periods = repo_summary['Periods']

        now = datetime.datetime.today().strftime('%c')
        
        repo_list = []

        for period in periods:
            # Calculate percentage free
            perc_free = round(period['FreeSpace'] / period['Capacity'] * 100, 2)
            period['percentage_free'] = perc_free
            period['message_type'] = 'repo'
            period['date'] = now
            repo_list.append(period)
        
        return repo_list

    def logout(self):
        '''
        Delete the session
        '''
        veeam_session = self.session.get('{}/logonSessions'.format(self.url)) 
        veeam_json = veeam_session.json()
        session_id = veeam_json['LogonSessions'][0]['SessionId']
        self.session.delete(
            '{}/logonSessions/{}'.format(self.url, session_id)
        )

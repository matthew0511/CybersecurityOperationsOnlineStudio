"""Isolated provider fakes. Production code has no test-mode scanner bypass."""
class FakeS3:
    def __init__(self):self.objects={};self.scan_status='NO_THREATS_FOUND'
    def put_object(self,**kwargs):
        version=str(len(self.objects)+1);self.objects[(kwargs['Key'],version)]=bytes(kwargs['Body']);return {'VersionId':version}
    def get_object_tagging(self,**kwargs):
        if (kwargs['Key'],kwargs.get('VersionId')) not in self.objects:raise ValueError('Version does not exist')
        return {'TagSet':[{'Key':'GuardDutyMalwareScanStatus','Value':self.scan_status}]}

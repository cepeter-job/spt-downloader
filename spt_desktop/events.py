"""Count-based progress never certifies a partial export as complete."""
from . import diagnostics


class Progress:
    def __init__(self,job_id,emit):
        self.job_id,self.emit = job_id,emit
        self.percent = 0
        self.terminal = False

    def _send(self,stage,percent,message,**values):
        if self.terminal:
            raise RuntimeError('Job already finished')
        # Progres hanya mengukur tahap pekerjaan; 100% dicadangkan untuk terminal COMPLETE.
        self.percent = max(self.percent,min(99,int(percent)))
        diagnostics.record('progress', level='DEBUG', job_id=self.job_id, stage=stage,
                           percent=self.percent, **{k:v for k,v in values.items() if k in diagnostics.COUNTERS})
        self.emit({'job_id':self.job_id,'type':'progress','stage':stage,
                   'percent':self.percent,'message':message,**values})

    @staticmethod
    def _fraction(done,total,empty=0):
        if not isinstance(done,int) or not isinstance(total,int) or not 0 <= done <= total:
            raise ValueError('Invalid progress denominator')
        return done/total if total else empty

    def authenticated(self):
        self._send('authentication',5,'Sesi Coretax siap.')

    def inventory(self,done,total,scanned):
        self._send('inventory',5+15*self._fraction(done,total),'Membaca daftar SPT…',
                   processed=done,total=total,scanned=scanned)

    def details(self,done,total,verified):
        if not 0 <= verified <= done: raise ValueError('Invalid verified count')
        self._send('details',20+70*self._fraction(done,total,empty=1),
                   f'SPT diproses {done}/{total}; terverifikasi {verified}.',
                   processed=done,total=total,verified=verified)

    def exported(self):
        self._send('export',95,'Workbook telah diekspor dan diverifikasi.')

    def publishing(self):
        self._send('publish',99,'Menyimpan workbook ke Downloads…')

    def finished(self,complete,output,status=None,message=None):
        if self.terminal: raise RuntimeError('Job already finished')
        if complete and not output: raise ValueError('COMPLETE requires verified output')
        self.terminal = True
        status = status or ('COMPLETE' if complete else 'PARTIAL')
        diagnostics.record('operation.finished', job_id=self.job_id, status=status, stage='finished')
        self.emit({'job_id':self.job_id,'type':'terminal','stage':'finished',
                   'percent':100 if complete else min(self.percent,99),
                   'status':status,'output':str(output) if output else None,
                   'message':message or ('Selesai; hasil terverifikasi.' if complete else 'PARTIAL: periksa Audit workbook.')})

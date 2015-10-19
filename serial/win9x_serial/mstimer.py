
import elapsedTimer


class MsTimer:
    def __init__(self):
        self.reset()

    def __call__(self):
        return elapsedTimer.elapsed(self.start)

    def reset(self):
        self.start = elapsedTimer.init()

if __name__ == '__main__':
    from criLib import *
    import win32api
    sTime = 1000
    elapsed = MsTimer()
    last = elapsed()
    while 1:
        print 'Sleep(%d)' % sTime
        win32api.Sleep(sTime)
        t = elapsed()
        diff = t - last
        print 'elapsed = %d' % diff
        last = t
        

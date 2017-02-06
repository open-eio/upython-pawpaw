DIRECTION_IN = 0
 
class Pin(object):
    IN = DIRECTION_IN
    def __init__(self, i, direction = DIRECTION_IN):
        self._i = i
        self._direction = direction
        self._value = False
    def __str__(self):
        return str(self._i)
    def value(self):
        return self._value
    def __setattr__(self, name, val):  #FIXME hacky way to mock value property and allow pin.value() calls
        if name == "value":
            self._value = val
        else:
            object.__setattr__(self,name,val)

if __name__ == "__main__":
    pin = Pin(0)

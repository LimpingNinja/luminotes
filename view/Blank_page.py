from Tags import Html, Head, Body, Script
from config.Version import VERSION


class Blank_page( Html ):
  def __init__( self, script = None ):
    if script:
      Html.__init__(
        self,
        Head(
          Script( type = u"text/javascript", src = u"/static/js/MochiKit.js?%s" % VERSION ),
        ),
        Body(
          Script( script, type = u"text/javascript" ),
        ),
      )
    else:
      Html.__init__(
        self,
        Head(),
        Body(),
      )

from Tags import Div, H3, A


class Link_area( Div ):
  def __init__( self, notebook_id ):
    Div.__init__(
      self,
      Div(
        id = u"notebook_name",
      ),
      Div(
        id = u"notebook_area",
      ),
    )
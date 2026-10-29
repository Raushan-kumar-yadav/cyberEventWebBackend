from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator

from app.core.clock import to_local

# IST in responses
LocalDatetime = Annotated[datetime, AfterValidator(to_local)]

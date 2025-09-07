from enum import Enum
import uuid

def new_uuid():
    """
    生成UUID
    """
    uuid_str = str(uuid.uuid4())
    uuid_str = uuid_str.replace("-", "")
    return uuid_str

class ODDTTS_TYPE(Enum):
    # 未知
    UNKNOWN = 0
    # ODD_GptSovits
    ODDTTS_GPTSOVITS = 1
    # EdgeTTS
    ODDTTS_EDGETTS = 2
    # ChatTTS
    ODDTTS_CHATTTS = 3
    # Bert Vits2
    ODDTTS_BERTVITS2 = 4
    # Bert Vits2 v2
    ODDTTS_BERTVITS2_V2 = 5

    def __str__(self):
        return self.name.title()
    

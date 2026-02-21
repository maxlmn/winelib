from enum import Enum

class UI(str, Enum):
    SELECT = "Select..."
    CREATE_NEW = "➕ Create New..."
    CREATE_NEW_WINE = "➕ Create New Wine..."
    CREATE_NEW_PLACE = "➕ Create New Place..."
    NEW_VINTAGE_SUFFIX = " - ➕ New Vintage"
    EXTERNAL = "External"
    
class BOTTLE_SIZES(str, Enum):
    S_75 = "75cl"
    S_37_5 = "37.5cl"
    S_150 = "150cl"
    S_300 = "300cl"
    S_600 = "600cl"
    
class CURRENCIES(str, Enum):
    SGD = "SGD"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"

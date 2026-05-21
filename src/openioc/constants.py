from enum import Enum

NS_V10 = "http://schemas.mandiant.com/2010/ioc"
NS_V11 = "http://openioc.org/schemas/OpenIOC_1.1"


class IndicatorOperator(str, Enum):
    AND = "AND"
    OR = "OR"


class Condition10(str, Enum):
    IS = "is"
    ISNOT = "isnot"
    CONTAINS = "contains"
    CONTAINSNOT = "containsnot"


class Condition11(str, Enum):
    IS = "is"
    CONTAINS = "contains"
    MATCHES = "matches"
    STARTS_WITH = "starts-with"
    ENDS_WITH = "ends-with"
    GREATER_THAN = "greater-than"
    LESS_THAN = "less-than"


CONDITION10_VALUES = {c.value for c in Condition10}
CONDITION11_VALUES = {c.value for c in Condition11}

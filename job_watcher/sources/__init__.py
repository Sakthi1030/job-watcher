from .ats import Greenhouse, Lever, SmartRecruiters, Workday
from .sites import Capgemini, Cognizant, DeloitteUSI

SOURCES = {
    "smartrecruiters": SmartRecruiters(),
    "greenhouse": Greenhouse(),
    "lever": Lever(),
    "workday": Workday(),
    "deloitte_usi": DeloitteUSI(),
    "capgemini": Capgemini(),
    "cognizant": Cognizant(),
}

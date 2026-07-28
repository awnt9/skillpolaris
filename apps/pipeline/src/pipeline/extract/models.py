from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

class JobRoomSwissRequestTemplate(BaseModel):
    cantonCodes: list = Field(default_factory=list)
    communalCodes:	list = Field(default_factory=list)
    companyName: Optional[str] = None
    displayRestricted:	bool = False
    keywords: list[str]
    onlineSince: int = 60
    permanent: Optional[bool] = None
    professionCodes: list = Field(default_factory=list)
    workloadPercentageMax: int = 100
    workloadPercentageMin: int = 10


class FranceTravailRequestTemplate(BaseModel):
    motsCles: str 
    accesTravailleurHandicape: bool = False
    appellation: Optional[str] = None
    codeNAF: Optional[str] = None
    codeROME: Optional[str] = None
    commune: Optional[str] = None
    departement: Optional[str] = None
    distance: Optional[int] = None
    domaine: Optional[str] = None
    dureeContratMax: Optional[str] = None #'double' format
    dureeContratMin: Optional[str] = None
    dureeHebdo: Optional[str] = None
    dureeHebdoMax: Optional[str] = None
    dureeHebdoMin: Optional[str] = None
    employeursHandiEngages: Optional[bool] = None
    entreprisesAdaptees: Optional[bool] = None
    experience: Optional[Literal["0", "1", "2", "3"]] = None
    experienceExigence: Optional[Literal["D", "S", "E"]] = None
    grandDomaine: Optional[str] = None
    inclureLimitrophes: bool = False
    maxCreationDate: Optional[str] = None # format ISO 8601
    minCreationDate: Optional[str] = None
    modeSelectionPartenaires: Optional[Literal["INCLUS", "EXCLU"]] = None
    natureContrat: Optional[str] = None
    niveauFormation: Optional[str] = None
    offresMRS: Optional[bool] = None
    offresManqueCandidats: Optional[bool] = None
    origineOffre: Optional[int] = None
    partenaires: Optional[str] = None
    paysContinent: Optional[str] = None
    periodeSalaire: Optional[Literal["M", "A", "H", "C"]] = None
    permis: Optional[str] = None
    publieeDesde: Optional[int] = None
    qualification: Optional[Literal["0", "9"]] = None
    range: str = "0-9" 
    region: Optional[str] = None
    salaireMin: Optional[str] = None
    secteurActivite: Optional[str] = None
    sort: Optional[int] = Field(default=1, ge=0, le=2) # 0, 1 or 2
    tempsPlein: Optional[bool] = None
    theme: Optional[str] = None
    typeContrat: Optional[str] = None

class USAJOBSRequestTemplate(BaseModel):
    # Basic parameters
    Keyword: str
    PositionTitle: Optional[str] = None
    
    # Salary
    RemunerationMinimumAmount: Optional[int] = None
    RemunerationMaximumAmount: Optional[int] = None
    SalaryBucket: Optional[str] = None  # Example: "25;50" (multiple values allowed)

    # Pay Grade -  "01" to "15"
    PayGradeHigh: Optional[str] = None
    PayGradeLow: Optional[str] = None
    GradeBucket: Optional[str] = None

    # Codes and Categories
    JobCategoryCode: Optional[str] = None # Example: "2210" for IT
    Organization: Optional[str] = None    # Organization code
    
    # Location
    LocationName: Optional[str] = None
    Radius: Optional[int] = None           # It is used together with LocationName
    RemoteIndicator: Optional[bool] = None # True just for remote
    
    # Filters
    PositionOfferingTypeCode: Optional[str] = None # 15317 for permanent
    PositionScheduleTypeCode: Optional[str] = None # 1 for Full-Time
    TravelPercentage: Optional[int] = None         # 0, 1, 2, 5, 7, 8
    
    # Candidates
    WhoMayApply: Optional[Literal["All", "Public", "Status"]] = "All"
    HiringPath: Optional[str] = None               # public, vet, disability, etc.
    DatePosted: Optional[int] = Field(None, ge=0, le=60) # Last X days
    
    # Pages
    Page: Optional[int] = 1
    ResultsPerPage: Optional[int] = Field(25, le=500)
    SortField: Optional[str] = None       # opendate, salarymin, location, etc.
    SortDirection: Optional[Literal["Asc", "Desc"]] = "Asc"
    
    # Detail on response
    Fields: Optional[Literal["Min", "Full"]] = "Full"


class StagedJobOffer(BaseModel):
    source: str
    external_id: str
    keyword: str | None = None
    title_raw: str
    description_raw: str
    url: str | None = None
    company_raw: str | None = None
    location_raw: str | None = None
    posted_at_raw: str | None = None
    raw_payload: dict[str, Any]
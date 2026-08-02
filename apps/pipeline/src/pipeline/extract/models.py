from typing import Literal, Optional

from pydantic import BaseModel, Field


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
    dureeContratMax: Optional[str] = None
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
    maxCreationDate: Optional[str] = None
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
    sort: Optional[int] = Field(default=1, ge=0, le=2)
    tempsPlein: Optional[bool] = None
    theme: Optional[str] = None
    typeContrat: Optional[str] = None


class USAJOBSRequestTemplate(BaseModel):
    Keyword: str
    PositionTitle: Optional[str] = None
    RemunerationMinimumAmount: Optional[int] = None
    RemunerationMaximumAmount: Optional[int] = None
    SalaryBucket: Optional[str] = None
    PayGradeHigh: Optional[str] = None
    PayGradeLow: Optional[str] = None
    GradeBucket: Optional[str] = None
    JobCategoryCode: Optional[str] = None
    Organization: Optional[str] = None
    LocationName: Optional[str] = None
    Radius: Optional[int] = None
    RemoteIndicator: Optional[bool] = None
    PositionOfferingTypeCode: Optional[str] = None
    PositionScheduleTypeCode: Optional[str] = None
    TravelPercentage: Optional[int] = None
    WhoMayApply: Optional[Literal["All", "Public", "Status"]] = "All"
    HiringPath: Optional[str] = None
    DatePosted: Optional[int] = Field(None, ge=0, le=60)
    Page: Optional[int] = 1
    ResultsPerPage: Optional[int] = Field(25, le=500)
    SortField: Optional[str] = None
    SortDirection: Optional[Literal["Asc", "Desc"]] = "Asc"
    Fields: Optional[Literal["Min", "Full"]] = "Full"

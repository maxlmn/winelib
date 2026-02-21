from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text, Index
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Region(Base):
    __tablename__ = 'regions'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    country = Column(String)
    color = Column(String)
    iso_code = Column(String(2))
    
    appellations = relationship("Appellation", back_populates="region_obj")
    producers = relationship("Producer", back_populates="region_obj")
    vineyards = relationship("Vineyard", back_populates="region_obj")
    wines = relationship("Wine", back_populates="region_obj")


class Appellation(Base):
    __tablename__ = 'appellations'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    region_id = Column(Integer, ForeignKey('regions.id'))
    subregion = Column(String)
    type = Column(String) # AOC, PDO, IG...
    details = Column(Text)
    colors = Column(String) # List of permitted colors
    
    # Winemap Integration
    location_link = Column(String)
    geojson = Column(Text)
    winemap_name = Column(String)
    
    # PDO Metadata
    pdo_id = Column(String)
    category = Column(String)
    varieties_text = Column(Text)
    max_yield_hl = Column(Float)
    max_yield_kg = Column(Integer)
    municipalities = Column(Text)
    registration_date = Column(Date)
    
    inao_id = Column(Integer, index=True)
    
    wines = relationship("Wine", back_populates="appellation")
    region_obj = relationship("Region", back_populates="appellations")

class Varietal(Base):
    __tablename__ = 'varietals'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    aliases = Column(String) # e.g. "Shiraz, Syrah"
    
    wines = relationship("Wine", back_populates="varietal") 


class Producer(Base):
    __tablename__ = 'producers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True) # e.g. "Domaine Leflaive"
    region_id = Column(Integer, ForeignKey('regions.id'))
    subregion = Column(String) # e.g. "Puligny-Montrachet"
    village = Column(String)
    winemaker = Column(String)
    owner = Column(String)
    type = Column(String) # domaine, maison, negoce
    importers = Column(String)
    notes = Column(Text) 
    description = Column(Text)
    profile_url = Column(String)
    lists = Column(String) # e.g. "[The New French Wine]"
    website = Column(String)
    # Relationships
    wines = relationship("Wine", back_populates="producer")
    region_obj = relationship("Region", back_populates="producers")

class Vineyard(Base):
    __tablename__ = 'vineyards'
    __table_args__ = (Index('idx_vineyard_name_region', 'name', 'region_id'),)
    #non unique as vineyards can have the same name in different regions and geodata would be in different files.abs
    #consider adding a column matchint to the file.
    id = Column(Integer, primary_key=True)
    vineyard_id = Column(Integer, index=True)
    name = Column(String, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'))
    sub_region = Column(String)
    village = Column(String)
    geojson = Column(Text)
    
    wines = relationship("Wine", back_populates="vineyard")
    region_obj = relationship("Region", back_populates="vineyards")

class Wine(Base):
    __tablename__ = 'wines'
    __table_args__ = (Index('idx_wine_lookup', 'producer_id', 'cuvee', 'appellation_id', 'varietal_id'),)
    
    id = Column(Integer, primary_key=True)
    producer_id = Column(Integer, ForeignKey('producers.id'))
    vineyard_id = Column(Integer, ForeignKey('vineyards.id'))
    
    cuvee = Column(String) # e.g. "Les Pucelles" (Raw)
    vintage = Column(String) # "2010" or "NV"
    disgorgement_date = Column(String) # e.g. "Oct 2024"
    type = Column(String)     # Red, White, Sparkling, Sweet
    region_id = Column(Integer, ForeignKey('regions.id'))
    appellation_id = Column(Integer, ForeignKey('appellations.id'))
    varietal_id = Column(Integer, ForeignKey('varietals.id'))
    appellation = relationship("Appellation", back_populates="wines")
    varietal = relationship("Varietal", back_populates="wines")
    vineyard = relationship("Vineyard", back_populates="wines")
    region_obj = relationship("Region", back_populates="wines")
    blend = Column(String) # e.g. "Bordeaux Blend"
    rp_score = Column(String) # Robert Parker Score
    rp_note = Column(Text)
    rp_url = Column(String)
    drink_window_start = Column(Integer)
    drink_window_end = Column(Integer)
    # Relationships
    producer = relationship("Producer", back_populates="wines")
    inventory = relationship("Bottle", back_populates="wine")

class Bottle(Base):
    """Represents physical inventory"""
    __tablename__ = 'cellar'
    
    id = Column(Integer, primary_key=True)
    wine_id = Column(Integer, ForeignKey('wines.id'))
    location = Column(String) # e.g. "Rack A-12", "Offsite"
    bottle_size = Column(String, default="750ml")
    qty = Column(Integer, default=1)
    purchase_date = Column(Date)
    price = Column(Float)
    currency = Column(String, default="EUR")
    vendor = Column(String)
    provenance = Column(String) # either importer / seller / restaurant name / person who brought the wine
    wine = relationship("Wine", back_populates="inventory")
    tastings = relationship("TastingNote", back_populates="bottle")

class TastingNote(Base):
    """Your personal log"""
    __tablename__ = 'tasting_notes'
    
    id = Column(Integer, primary_key=True)
    bottle_id = Column(Integer, ForeignKey('cellar.id'), nullable=False)
    date = Column(Date)
    rating = Column(Integer) # Your 100pt score
    notes = Column(Text)     # "Explosive nose of..."
    tags = Column(String)    # "Dinner, Gift, corked"
    location = Column(String) ## will be set to place name automatically.
    sequence = Column(Integer) # Sequence in the tasting day (Seq)
    glasses = Column(Float)    # Amount drank in glasses (Gls)
    # Relationships
    bottle = relationship("Bottle", back_populates="tastings")
    place_id = Column(Integer, ForeignKey('places.id'))
    place = relationship("Place", back_populates="tastings")

class Place(Base):
    __tablename__ = 'places'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True) # e.g. "Home", "Odette"
    
    city = Column(String)
    country = Column(String)
    type = Column(String) # Restaurant, Home, Bar, etc.
    michelin_stars = Column(Integer)
    notes = Column(Text)
    lat = Column(Float)
    lng = Column(Float)
    
    tastings = relationship("TastingNote", back_populates="place")
    visits = relationship("RestaurantVisit", back_populates="place")

class RestaurantVisit(Base):
    __tablename__ = 'restaurants_visits'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    place_id = Column(Integer, ForeignKey('places.id'))
    notes = Column(Text)
    
    place = relationship("Place", back_populates="visits")

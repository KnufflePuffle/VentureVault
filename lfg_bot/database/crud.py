from sqlalchemy.orm import Session
from . import models


# Campaign CRUD operations
def create_campaign(db: Session, name: str, description: str, dm_id: str):
    """Create a new campaign"""
    campaign = models.Campaign(name=name, description=description, dm_id=dm_id)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def get_campaign(db: Session, campaign_id: int):
    """Get a campaign by ID"""
    return db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()


def get_campaigns_by_dm(db: Session, dm_id: str):
    """Get all campaigns for a DM"""
    return db.query(models.Campaign).filter(models.Campaign.dm_id == dm_id).all()


def update_campaign(db: Session, campaign_id: int, **kwargs):
    """Update campaign details"""
    campaign = get_campaign(db, campaign_id)
    if not campaign:
        return None

    for key, value in kwargs.items():
        if hasattr(campaign, key):
            setattr(campaign, key, value)

    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(db: Session, campaign_id: int):
    """Delete a campaign"""
    campaign = get_campaign(db, campaign_id)
    if not campaign:
        return False

    db.delete(campaign)
    db.commit()
    return True


# Plot Point CRUD operations
def create_plot_point(db: Session, campaign_id: int, title: str, description: str):
    """Create a new plot point"""
    plot_point = models.PlotPoint(campaign_id=campaign_id, title=title, description=description)
    db.add(plot_point)
    db.commit()
    db.refresh(plot_point)
    return plot_point


def get_plot_point(db: Session, plot_id: int):
    """Get a plot point by ID"""
    return db.query(models.PlotPoint).filter(models.PlotPoint.id == plot_id).first()


def get_plot_points_by_campaign(db: Session, campaign_id: int):
    """Get all plot points for a campaign"""
    return db.query(models.PlotPoint).filter(models.PlotPoint.campaign_id == campaign_id).all()


def update_plot_point(db: Session, plot_id: int, **kwargs):
    """Update plot point details"""
    plot_point = get_plot_point(db, plot_id)
    if not plot_point:
        return None

    for key, value in kwargs.items():
        if hasattr(plot_point, key):
            setattr(plot_point, key, value)

    db.commit()
    db.refresh(plot_point)
    return plot_point


def delete_plot_point(db: Session, plot_id: int):
    """Delete a plot point"""
    plot_point = get_plot_point(db, plot_id)
    if not plot_point:
        return False

    db.delete(plot_point)
    db.commit()
    return True
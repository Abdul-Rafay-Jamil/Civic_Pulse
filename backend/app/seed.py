"""Idempotent seed command — loads ≥ 30 realistic complaints.

Running it twice must not duplicate rows (idempotent via deterministic UUIDs).
Complaints are in Urdu-influenced English, spread across categories.
"""

import asyncio
import uuid
import os
import sys
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Complaint, Base


# Deterministic UUID from seed index — running twice produces the same UUIDs
def _seed_uuid(index: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"civicpulse-seed-{index}")


SEED_COMPLAINTS = [
    # === WATER (6 complaints) ===
    {
        "text": "Burst water main flooding Street 12 since fajr, water entering ground floors of houses. Please send repair team urgently, children cannot go to school.",
        "location": "Street 12, Gulberg III, Lahore",
        "reporter_contact": "0300-1234567",
        "category": "water",
        "priority": "high",
        "ai_summary": "Burst water main flooding residential street since early morning",
        "triaged_by": "seed",
    },
    {
        "text": "Paani ki supply band hai pichle teen din se. Tanker bhi nahi aaya. Bache aur budhay log pareshan hain, koi solution dein please.",
        "location": "Block C, North Nazimabad, Karachi",
        "reporter_contact": "0321-9876543",
        "category": "water",
        "priority": "high",
        "ai_summary": "No water supply for three days, tanker service also absent",
        "triaged_by": "seed",
    },
    {
        "text": "Sewage line overflowing near the masjid. The nala is blocked and dirty water is going into people's homes. Very bad smell, mosquitoes everywhere.",
        "location": "Mohalla Shah Faisal, Rawalpindi",
        "reporter_contact": None,
        "category": "water",
        "priority": "high",
        "ai_summary": "Sewage overflow near mosque, water entering homes",
        "triaged_by": "seed",
    },
    {
        "text": "Water pressure is very low in our area since last week. We are getting water only for 30 minutes in the morning. This is not enough for a family of 8.",
        "location": "Sector I-10/2, Islamabad",
        "reporter_contact": "0333-5551234",
        "category": "water",
        "priority": "normal",
        "ai_summary": "Low water pressure, only 30 minutes supply daily",
        "triaged_by": "seed",
    },
    {
        "text": "Underground water tank in the park is leaking. Water wasting ho raha hai continuously. The leak has been there for at least two weeks now.",
        "location": "Jinnah Park, Model Town, Lahore",
        "reporter_contact": None,
        "category": "water",
        "priority": "normal",
        "ai_summary": "Underground tank leaking in park for two weeks",
        "triaged_by": "seed",
    },
    {
        "text": "The tap water has turned yellowish colour and has a bad taste. We think the filtration plant is not working properly. Can someone check?",
        "location": "Phase 5, DHA, Lahore",
        "reporter_contact": "0345-7778899",
        "category": "water",
        "priority": "normal",
        "ai_summary": "Discoloured tap water with bad taste, possible filtration issue",
        "triaged_by": "seed",
    },
    # === ELECTRICITY (5 complaints) ===
    {
        "text": "Bijli ka transformer phat gaya raat ko 2 baje. Poora mohalla andhera mein hai. Budhay log aur beemar patients ko bahut takleef ho rahi hai.",
        "location": "Gulshan-e-Iqbal Block 6, Karachi",
        "reporter_contact": "0312-4445566",
        "category": "electricity",
        "priority": "high",
        "ai_summary": "Transformer exploded at 2am, entire neighbourhood in darkness",
        "triaged_by": "seed",
    },
    {
        "text": "Electric wire hanging low on the main road near school. Very dangerous for children, especially during rain. Some wires are sparking at night.",
        "location": "Mall Road near Govt Boys School, Murree",
        "reporter_contact": "0300-9998877",
        "category": "electricity",
        "priority": "high",
        "ai_summary": "Low-hanging sparking electric wires near school on main road",
        "triaged_by": "seed",
    },
    {
        "text": "Load shedding is happening 8 hours daily in our area but the schedule says only 4 hours. UPS and generator dono kharab ho gaye because of voltage fluctuation.",
        "location": "Satellite Town, Rawalpindi",
        "reporter_contact": None,
        "category": "electricity",
        "priority": "normal",
        "ai_summary": "Excessive load shedding beyond schedule with voltage issues",
        "triaged_by": "seed",
    },
    {
        "text": "The electricity meter is running very fast, bill doubled this month. We did not increase usage. Please send someone to check the meter.",
        "location": "Officers Colony, Faisalabad",
        "reporter_contact": "0321-1112233",
        "category": "electricity",
        "priority": "low",
        "ai_summary": "Suspected faulty meter causing inflated electricity bill",
        "triaged_by": "seed",
    },
    {
        "text": "Street pole with electricity connection is tilting badly after the storm. It can fall any time on the road or on cars parked below.",
        "location": "University Road, Peshawar",
        "reporter_contact": "0345-6667788",
        "category": "electricity",
        "priority": "high",
        "ai_summary": "Tilting electricity pole at risk of collapse after storm",
        "triaged_by": "seed",
    },
    # === SANITATION (5 complaints) ===
    {
        "text": "Kachra teen din se nahi uthaya gaya, billi aur kuttay sara garbage phaila dete hain roz subah. Bachon ko dengue ka khatra hai, please send sweepers.",
        "location": "Johar Town Block D, Lahore",
        "reporter_contact": "0333-2221100",
        "category": "sanitation",
        "priority": "high",
        "ai_summary": "Garbage not collected for three days, dengue risk from stagnant waste",
        "triaged_by": "seed",
    },
    {
        "text": "The dustbins placed by TMA are overflowing and nobody comes to empty them. The smell is unbearable, especially in the evening time.",
        "location": "Commercial Market, Rawalpindi",
        "reporter_contact": None,
        "category": "sanitation",
        "priority": "normal",
        "ai_summary": "Overflowing dustbins with no regular collection",
        "triaged_by": "seed",
    },
    {
        "text": "Construction waste dumped on empty plot next to our house. Mosquitoes breeding in collected rainwater. Nobody is taking responsibility for cleaning.",
        "location": "Bahria Town Phase 4, Rawalpindi",
        "reporter_contact": "0300-5554433",
        "category": "sanitation",
        "priority": "normal",
        "ai_summary": "Construction waste dumped near residential area causing mosquito breeding",
        "triaged_by": "seed",
    },
    {
        "text": "The public toilet in the park is in terrible condition. No water supply, no cleaning for weeks. It should be either maintained or closed permanently.",
        "location": "Race Course Park, Lahore",
        "reporter_contact": None,
        "category": "sanitation",
        "priority": "normal",
        "ai_summary": "Unmaintained public toilet in park with no water",
        "triaged_by": "seed",
    },
    {
        "text": "Dead animal carcass lying on the road since yesterday morning. Very bad smell and health hazard. Municipal workers passed by but did not remove it.",
        "location": "GT Road near Gujar Khan",
        "reporter_contact": "0312-8889900",
        "category": "sanitation",
        "priority": "high",
        "ai_summary": "Animal carcass on road for over 24 hours, health hazard",
        "triaged_by": "seed",
    },
    # === ROADS (5 complaints) ===
    {
        "text": "Bohut bara pothole hai main road pe, raat ko ek motorcycle wala gir gaya. Hospital le ke jaana pada. Koi repair karo jaldi, ek jaan gai toh?",
        "location": "Multan Road near Thokar Niaz Baig, Lahore",
        "reporter_contact": "0321-7776655",
        "category": "roads",
        "priority": "high",
        "ai_summary": "Dangerous pothole on main road caused motorcycle accident",
        "triaged_by": "seed",
    },
    {
        "text": "Road construction started three months ago and still not completed. Half the road is dug up, no barriers, no warning signs at night. Very dangerous.",
        "location": "Kashmir Highway near Faizabad, Islamabad",
        "reporter_contact": None,
        "category": "roads",
        "priority": "high",
        "ai_summary": "Incomplete road construction for 3 months with no safety barriers",
        "triaged_by": "seed",
    },
    {
        "text": "The speed breaker near the school is too high, it damages cars and makes ambulances slow down too much. It needs to be resized according to standards.",
        "location": "Main Boulevard, Gulberg, Lahore",
        "reporter_contact": "0333-4443322",
        "category": "roads",
        "priority": "low",
        "ai_summary": "Oversized speed breaker near school damaging vehicles",
        "triaged_by": "seed",
    },
    {
        "text": "Footpath tiles are broken and uneven near the bus stop. Old people and disabled persons cannot walk safely. Some tiles are completely missing.",
        "location": "Blue Area, Islamabad",
        "reporter_contact": None,
        "category": "roads",
        "priority": "normal",
        "ai_summary": "Broken and uneven footpath tiles at bus stop, accessibility issue",
        "triaged_by": "seed",
    },
    {
        "text": "After yesterday rain, the entire road is flooded because drain covers are blocked. Traffic cannot pass and water entering into shops on both sides.",
        "location": "Anarkali Bazaar, Lahore",
        "reporter_contact": "0300-1110099",
        "category": "roads",
        "priority": "high",
        "ai_summary": "Road flooding due to blocked drain covers after rain",
        "triaged_by": "seed",
    },
    # === STREETLIGHTS (5 complaints) ===
    {
        "text": "Street light band hai pichle ek hafte se gali mein. Raat ko bilkul andhera rehta hai, chori ka khatara badh gaya hai. Koi electrician bhejo.",
        "location": "Street 4, Westridge, Rawalpindi",
        "reporter_contact": "0345-2223344",
        "category": "streetlights",
        "priority": "normal",
        "ai_summary": "Street light not working for a week, security concerns",
        "triaged_by": "seed",
    },
    {
        "text": "Three street lights on our road are flickering continuously. At night it looks very strange and one light is making buzzing sound. Possible short circuit hazard.",
        "location": "Cantt Area, Lahore",
        "reporter_contact": "0312-5556677",
        "category": "streetlights",
        "priority": "normal",
        "ai_summary": "Flickering and buzzing street lights, possible short circuit",
        "triaged_by": "seed",
    },
    {
        "text": "New LED street lights installed last month are too dim. The old sodium lights were much better. The park area especially is very dark now.",
        "location": "F-7 Markaz, Islamabad",
        "reporter_contact": None,
        "category": "streetlights",
        "priority": "low",
        "ai_summary": "Newly installed LED lights too dim compared to old sodium lights",
        "triaged_by": "seed",
    },
    {
        "text": "The street light pole near the intersection is damaged and the light is hanging by the wire. Very dangerous, especially when it is windy.",
        "location": "Shahrah-e-Faisal, Karachi",
        "reporter_contact": "0300-8887766",
        "category": "streetlights",
        "priority": "high",
        "ai_summary": "Damaged street light pole with light hanging by wire",
        "triaged_by": "seed",
    },
    {
        "text": "All six street lights in our cul-de-sac have been off since load shedding two days ago. They did not come back when electricity was restored. Timer issue maybe?",
        "location": "DHA Phase 2, Islamabad",
        "reporter_contact": "0321-3334455",
        "category": "streetlights",
        "priority": "normal",
        "ai_summary": "Six street lights not restored after power outage, possible timer fault",
        "triaged_by": "seed",
    },
    # === OTHER (4 complaints) ===
    {
        "text": "Stray dogs in our neighbourhood have become very aggressive. They chase children going to school in the morning. Someone was bitten last week.",
        "location": "Township, Lahore",
        "reporter_contact": "0333-9998877",
        "category": "other",
        "priority": "high",
        "ai_summary": "Aggressive stray dogs chasing and biting children near school",
        "triaged_by": "seed",
    },
    {
        "text": "The park near our house has no boundary wall. People use it as parking at night and drug addicts gather there. It is not safe for families.",
        "location": "G-9 Markaz, Islamabad",
        "reporter_contact": None,
        "category": "other",
        "priority": "normal",
        "ai_summary": "Park without boundary wall used for parking and unsafe activities",
        "triaged_by": "seed",
    },
    {
        "text": "Loud construction noise from the new plaza building site starts at 6am every day including weekends. It is affecting our sleep and health. Please enforce timings.",
        "location": "Johar Town, Lahore",
        "reporter_contact": "0345-1112233",
        "category": "other",
        "priority": "normal",
        "ai_summary": "Construction noise at 6am daily including weekends, no timing enforcement",
        "triaged_by": "seed",
    },
    {
        "text": "Illegal encroachment of footpath by shop owners on the main market road. Pedestrians are forced to walk on the road. Traffic police does nothing.",
        "location": "Liberty Market, Lahore",
        "reporter_contact": "0300-4445566",
        "category": "other",
        "priority": "normal",
        "ai_summary": "Footpath encroachment by shops forcing pedestrians onto road",
        "triaged_by": "seed",
    },
]


async def seed_database(database_url: str | None = None) -> None:
    """Idempotent seed — uses deterministic UUIDs so running twice doesn't duplicate."""
    url = database_url or os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://civicpulse:civicpulse@localhost:5432/civicpulse",
    )

    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        for i, data in enumerate(SEED_COMPLAINTS):
            seed_id = _seed_uuid(i)

            # Check if already exists (idempotent)
            existing = await session.execute(
                select(Complaint.id).where(Complaint.id == seed_id)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            now = datetime.now(UTC)
            complaint = Complaint(
                id=seed_id,
                text=data["text"],
                location=data["location"],
                reporter_contact=data.get("reporter_contact"),
                category=data["category"],
                priority=data["priority"],
                status="open",
                ai_summary=data["ai_summary"],
                triaged_by=data["triaged_by"],
                triage_latency_ms=0,
                created_at=now,
                updated_at=now,
            )
            session.add(complaint)

        await session.commit()

    await engine.dispose()
    print(f"Seeded {len(SEED_COMPLAINTS)} complaints (idempotent).")


if __name__ == "__main__":
    asyncio.run(seed_database())

"""Deterministic SYNTHETIC data generator. Nothing here is real supplier, price or customer data."""
from __future__ import annotations
import numpy as np

# name, country, region, lat, lon, price multiplier vs Dubai, tags
DEST = [
 ("Dubai","UAE","Middle East",25.20,55.27,1.0,"city luxury adventure family"),("Abu Dhabi","UAE","Middle East",24.45,54.38,1.0,"culture luxury family"),
 ("Singapore","Singapore","Southeast Asia",1.29,103.85,1.2,"city family culture"),("Bangkok","Thailand","Southeast Asia",13.75,100.50,0.6,"city culture budget"),
 ("Phuket","Thailand","Southeast Asia",7.88,98.39,0.65,"beach adventure couple"),("Bali","Indonesia","Southeast Asia",-8.41,115.19,0.65,"beach culture couple adventure"),
 ("Maldives","Maldives","South Asia",3.20,73.22,2.0,"beach luxury couple relaxation"),("Paris","France","Europe",48.86,2.35,1.5,"city culture couple"),
 ("London","UK","Europe",51.51,-0.13,1.6,"city culture family"),("Switzerland","Switzerland","Europe",46.82,8.23,2.0,"adventure couple luxury"),
 ("Thailand","Thailand","Southeast Asia",13.0,101.0,0.6,"beach culture budget"),("Malaysia","Malaysia","Southeast Asia",3.14,101.69,0.55,"city family budget"),
 ("Vietnam","Vietnam","Southeast Asia",16.05,108.2,0.5,"culture beach budget"),("Sri Lanka","Sri Lanka","South Asia",6.93,79.86,0.5,"beach culture adventure"),
 ("Nepal","Nepal","South Asia",27.7,85.3,0.4,"adventure culture budget"),("Japan","Japan","East Asia",35.68,139.69,1.4,"city culture family"),
 ("Australia","Australia","Oceania",-33.87,151.21,1.7,"adventure family city"),
]
AREAS = {"Dubai":["Downtown","Marina","Palm Jumeirah","Deira","Jumeirah"],"Singapore":["Marina Bay","Sentosa","Orchard","Chinatown"],
 "Bangkok":["Sukhumvit","Riverside","Silom","Old Town"],"Bali":["Seminyak","Ubud","Nusa Dua","Uluwatu"],"Paris":["Le Marais","Louvre","Montmartre","Eiffel"]}
HOTEL_TYPES = {
 "city":"central business district hotel near shopping and metro with modern rooms and skyline views",
 "beach":"peaceful beachfront property with sea views, quiet and relaxing, ideal for couples",
 "luxury":"luxury resort with spa, fine dining and private pool, romantic premium stay",
 "value":"comfortable budget friendly hotel with good breakfast and clean simple rooms, great value",
 "couple":"romantic boutique hotel for couples with rooftop sunset dinners, quiet and intimate",
 "family":"family resort with kids club, large pool and spacious rooms, family friendly"}
# (suffix, category, hours, base INR, family, couple, adv, relax, culture, keywords)
ACT_TYPES = [("Sunset Cruise","cruise",2,3200,.7,.95,.1,.8,.2,"cruise"),("Guided City Tour","sightseeing",4,2600,.8,.6,.1,.4,.7,"city tour|sightseeing"),
 ("Cultural Show & Dinner","culture",3,3000,.7,.7,.1,.5,.9,"show|cultural"),("Adventure Park","adventure",5,4800,.8,.4,.9,.1,.1,"adventure|theme park"),
 ("Food Walking Tour","food",3,2200,.6,.7,.1,.5,.6,"food"),("Beach Day Pass","beach",4,1800,.8,.8,.2,.9,.1,"beach"),
 ("Museum Visit","culture",2.5,1900,.7,.5,.0,.5,.95,"museum"),("Spa Retreat","relaxation",2,3500,.2,.95,.0,1.0,.2,"spa")]
DUBAI_ACTS = [  # publicly known attractions; prices/durations are synthetic
 ("Burj Khalifa At The Top","Downtown",25.1972,55.2744,2,5500,"sightseeing","burj|khalifa"),("Dubai Mall & Aquarium","Downtown",25.1985,55.2796,3,1800,"sightseeing","mall|aquarium"),
 ("Desert Safari with BBQ Dinner","Desert",24.9,55.5,6,4200,"adventure","safari|desert"),("Dubai Marina Cruise","Marina",25.0805,55.1403,2,3200,"cruise","marina|cruise"),
 ("Dubai Frame","Jumeirah",25.2349,55.3004,1.5,1500,"sightseeing","frame"),("Museum of the Future","Downtown",25.2195,55.2818,2.5,3600,"culture","museum"),
 ("Palm Jumeirah Tour","Palm Jumeirah",25.1124,55.139,3,2900,"sightseeing","palm"),("Aquaventure Waterpark","Palm Jumeirah",25.1304,55.1171,5,6400,"adventure","aqua|waterpark"),
 ("Old Dubai & Souks","Deira",25.2697,55.2972,3,1600,"culture","old dubai|souk"),("Sheikh Zayed Grand Mosque Tour","Abu Dhabi",24.4129,54.4749,6,3800,"culture","mosque|zayed")]
FN = ["Aarav","Priya","Rohan","Ananya","Vikram","Neha","Arjun","Meera","Kabir","Isha","Sanjay","Divya","Rahul","Pooja","Amit","Kavya"]
LN = ["Sharma","Verma","Iyer","Nair","Gupta","Mehta","Reddy","Singh","Kapoor","Bose","Joshi","Patel","Khan","Das"]
PRE = ["Azure","Royal","Pearl","Coral","Grand","Haven","Skyline","Palm","Oasis","Lotus","Crown","Harbor","Sunset","Orchid","Zenith"]
SUF = ["Suites","Resort","Hotel","Residence","Retreat","Inn"]
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def _areas(dest: str) -> list[str]:
    return AREAS.get(dest, ["Central", "Old Town", "Waterfront", "Resort Belt"])


def generate(seed: int = 42, n_suppliers: int = 120, hotels_per_dest: int = 32, acts_per_dest: int = 30, n_customers: int = 1000) -> dict[str, list[dict]]:
    """Return all synthetic tables as lists of dicts. Fully deterministic for a given seed."""
    rng = np.random.default_rng(seed)
    sup = []
    for i in range(n_suppliers):
        q = float(rng.beta(5, 2))  # latent quality drives correlated metrics
        sup.append(dict(id=f"S{i+1:03d}", name=f"Supplier {i+1:03d}", confirmation_rate=round(min(.99, .62 + .37 * q + rng.normal(0, .02)), 3),
            response_time_h=round(max(1.0, 42 - 36 * q + rng.normal(0, 3)), 1), cancellation_rate=round(max(.005, .13 - .11 * q + rng.normal(0, .008)), 3),
            availability_rate=round(min(.99, .7 + .29 * q), 3), complaints_per_1k=round(max(0, 9 - 8 * q + rng.normal(0, .6)), 2),
            price_competitiveness=round(float(np.clip(.3 + .6 * q + rng.normal(0, .08), 0, 1)), 3), price_volatility=round(float(np.clip(.25 - .2 * q + rng.normal(0, .03), .01, .5)), 3)))
    sup[7].update(confirmation_rate=0.71, cancellation_rate=0.12, response_time_h=34.0)  # scenario: a known risky supplier
    sids = [s["id"] for s in sup]; squal = {s["id"]: s["confirmation_rate"] for s in sup}

    dests = []
    for i, (n, c, r, la, lo, m, tags) in enumerate(DEST):
        t = set(tags.split()); sc = {k: round(float(np.clip(.35 + .5 * (k in t or (k == "relaxation" and "beach" in t)) + rng.normal(0, .06), 0, 1)), 2) for k in ["family", "couple", "adventure", "luxury", "relaxation", "city", "beach", "culture"]}
        dests.append(dict(id=f"D{i+1:02d}", name=n, country=c, region=r, description=f"{n} is a {tags} destination (synthetic description).", best_months=[MONTHS[(k + 9) % 12] for k in range(5)],
            average_duration=int(4 + 3 * (m > 1.3) + rng.integers(0, 3)), budget_category="premium" if m >= 1.4 else "mid" if m >= .8 else "value", scores=sc,
            visa_note="Visa rules not modelled in this prototype; verify with an official source.", lat=la, lon=lo, price_multiplier=m))

    hotels, acts, transfers = [], [], []
    for d in dests:
        areas = _areas(d["name"]); m = d["price_multiplier"]; acenter = {a: (d["lat"] + rng.normal(0, .06), d["lon"] + rng.normal(0, .06)) for a in areas}
        for _ in range(hotels_per_dest):
            star = int(rng.choice([3, 4, 5], p=[.3, .42, .28]))
            typ = "luxury" if star == 5 and rng.random() < .6 else str(rng.choice(["value", "city", "value"] if star == 3 else ["city", "beach", "couple", "family"] if star == 5 else ["city", "beach", "couple", "family", "value"]))
            area = str(rng.choice(areas)); sid = str(rng.choice(sids)); lat, lon = acenter[area]
            price = round(float({3: 5500, 4: 9000, 5: 17000}[star] * m * (.8 + rng.random() * .5) * {"luxury": 1.3, "value": .85}.get(typ, 1.0)) / 100) * 100
            rating = round(float(np.clip(3.0 + .3 * (star - 3) + rng.random() * 1.3 + (squal[sid] - .8) * .5, 3.0, 4.9)), 1)
            hotels.append(dict(id=f"H{len(hotels)+1:04d}", name=f"{rng.choice(PRE)} {area.split()[0]} {rng.choice(SUF)}", destination=d["name"], area=area, star_rating=star, hotel_type=typ,
                latitude=round(lat + rng.normal(0, .008), 5), longitude=round(lon + rng.normal(0, .008), 5), description=f"{star}-star {HOTEL_TYPES[typ]} in {area}, {d['name']}",
                amenities=[a for a in ["pool", "spa", "gym", "wifi", "breakfast", "kids club", "beach access", "rooftop bar"] if rng.random() < .3 + .1 * (star - 3)],
                room_types=["Standard", "Deluxe"] + (["Suite"] if star >= 4 else []), base_price_per_night=float(price), meal_plan="Breakfast" if star >= 4 or rng.random() < .6 else "Room only",
                rating=rating, review_count=int(80 + rng.random() * 3000), family_friendly=typ in ("family", "city", "value", "beach"), couple_friendly=typ in ("couple", "beach", "luxury"),
                luxury_score=round(star / 5 * (1.1 if typ == "luxury" else 1), 2), budget_score=round(1 - star / 6, 2), location_score=round(float(.4 + rng.random() * .6), 2),
                margin_pct=round(float(.1 + rng.random() * .06 if squal[sid] > .85 else .07 + rng.random() * .05), 3), supplier_id=sid,
                availability=bool(rng.random() < (.88 + .1 * squal[sid] / 1)) and bool(rng.random() > .04), cancellation_policy=str(rng.choice(["Free cancel 7d", "Free cancel 3d", "Non-refundable"]))))
        made = 0
        if d["name"] == "Dubai":
            for n, area, la, lo, h, p, cat, kw in DUBAI_ACTS:
                acts.append(_act(len(acts), rng, sids, n, d["name"], area, la, lo, h, p, cat, kw, "")); made += 1
        for area in areas:
            for suf, cat, h, p, fam, cou, adv, rel, cul, kw in ACT_TYPES:
                if made >= acts_per_dest: break
                la, lo = acenter[area]
                acts.append(_act(len(acts), rng, sids, f"{area} {suf}", d["name"], area, la + rng.normal(0, .004), lo + rng.normal(0, .004), h, p * m, cat, kw, (fam, cou, adv, rel, cul))); made += 1
        for kind, veh, cap, p, pp, dur in [("airport_private", "Sedan", 3, 4200, False, 40), ("airport_private", "Van", 6, 6500, False, 40), ("airport_shared", "Shared shuttle", 10, 1800, True, 60), ("intercity", "Coach", 30, 2500, True, 150)]:
            transfers.append(dict(id=f"T{len(transfers)+1:04d}", destination=d["name"], kind=kind, vehicle_type=veh, capacity=cap, price=round(p * m / 50) * 50.0, per_person=pp, duration_min=dur, availability=True, supplier_id=str(rng.choice(sids))))
    names = lambda: f"{rng.choice(FN)} {rng.choice(LN)}"
    customers = []
    dn = [d["name"] for d in dests]
    for i in range(n_customers):
        t = str(rng.choice(["couple", "family", "solo", "business", "group"], p=[.3, .3, .1, .15, .15])); bud = float(round(rng.lognormal(11.6 + (t == "family") * .3, .4), -3))
        customers.append(dict(id=f"C{i+1:05d}", name=names(), country="India", city=str(rng.choice(["Delhi", "Mumbai", "Bengaluru", "Pune", "Chennai", "Kolkata"])), traveler_type=t, preferred_budget=bud,
            preferred_destinations=list(rng.choice(dn, 2, replace=False)), preferred_travel_style=str(rng.choice(["relaxed", "balanced", "packed"], p=[.45, .4, .15] if t != "business" else [.1, .5, .4])), preferred_activities=list(rng.choice([a[0] for a in ACT_TYPES], 2, replace=False))))
    return dict(suppliers=sup, destinations=dests, hotels=hotels, activities=acts, transfers=transfers, customers=customers)


def _act(i, rng, sids, name, dest, area, la, lo, hrs, price, cat, kw, sc):
    fam, cou, adv, rel, cul = sc if sc else {"adventure": (.8, .4, .9, .1, .1), "culture": (.7, .5, .0, .5, .95), "cruise": (.7, .95, .1, .8, .2)}.get(cat, (.8, .6, .2, .4, .5))
    return dict(id=f"A{i+1:04d}", name=name, destination=dest, area=area, category=cat, description=f"{cat} experience: {name} in {dest}", keywords=kw, latitude=round(float(la), 5), longitude=round(float(lo), 5),
        duration_hours=float(hrs), price_per_person=float(round(price * (.9 + rng.random() * .2) / 100) * 100), rating=round(float(4 + rng.random() * .9), 1), review_count=int(50 + rng.random() * 5000),
        family_friendly=fam >= .6, couple_friendly=cou >= .6, adventure_score=adv, relaxation_score=rel, culture_score=cul, popularity_score=round(float(rng.random()), 2),
        availability=bool(rng.random() > .03), supplier_id=str(rng.choice(sids)))

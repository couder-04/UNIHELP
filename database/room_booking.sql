--
-- PostgreSQL database dump
--

\restrict aTVG18a9Jbkbq9OcDvGdIYY8cUoe9It3GsUMgaCrmLhHgIGyPZddZZGGYJpKSr7

-- Dumped from database version 16.15
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.rooms DROP CONSTRAINT IF EXISTS rooms_facility_id_fkey;
ALTER TABLE IF EXISTS ONLY public.requests DROP CONSTRAINT IF EXISTS requests_room_id_fkey;
ALTER TABLE IF EXISTS ONLY public.bookings DROP CONSTRAINT IF EXISTS bookings_room_id_fkey;
DROP TRIGGER IF EXISTS trg_requests_updated_at ON public.requests;
DROP TRIGGER IF EXISTS trg_bookings_updated_at ON public.bookings;
DROP INDEX IF EXISTS public.idx_requests_status;
DROP INDEX IF EXISTS public.idx_requests_room_date;
DROP INDEX IF EXISTS public.idx_requests_requester;
DROP INDEX IF EXISTS public.idx_history_entity;
DROP INDEX IF EXISTS public.idx_bookings_room_date;
DROP INDEX IF EXISTS public.idx_bookings_guest_dates;
DROP INDEX IF EXISTS public.idx_bookings_booker;
ALTER TABLE IF EXISTS ONLY public.rooms DROP CONSTRAINT IF EXISTS rooms_room_code_key;
ALTER TABLE IF EXISTS ONLY public.rooms DROP CONSTRAINT IF EXISTS rooms_pkey;
ALTER TABLE IF EXISTS ONLY public.rooms DROP CONSTRAINT IF EXISTS rooms_facility_id_room_code_key;
ALTER TABLE IF EXISTS ONLY public.requests DROP CONSTRAINT IF EXISTS requests_pkey;
ALTER TABLE IF EXISTS ONLY public.bookings DROP CONSTRAINT IF EXISTS no_overlapping_hourly_bookings;
ALTER TABLE IF EXISTS ONLY public.bookings DROP CONSTRAINT IF EXISTS no_overlapping_daily_bookings;
ALTER TABLE IF EXISTS ONLY public.facilities DROP CONSTRAINT IF EXISTS facilities_pkey;
ALTER TABLE IF EXISTS ONLY public.facilities DROP CONSTRAINT IF EXISTS facilities_name_key;
ALTER TABLE IF EXISTS ONLY public.facilities DROP CONSTRAINT IF EXISTS facilities_facility_type_key;
ALTER TABLE IF EXISTS ONLY public.bookings DROP CONSTRAINT IF EXISTS bookings_pkey;
ALTER TABLE IF EXISTS ONLY public.booking_history DROP CONSTRAINT IF EXISTS booking_history_pkey;
ALTER TABLE IF EXISTS public.rooms ALTER COLUMN room_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.requests ALTER COLUMN request_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.facilities ALTER COLUMN facility_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.bookings ALTER COLUMN booking_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.booking_history ALTER COLUMN history_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.rooms_room_id_seq;
DROP TABLE IF EXISTS public.rooms;
DROP SEQUENCE IF EXISTS public.requests_request_id_seq;
DROP TABLE IF EXISTS public.requests;
DROP SEQUENCE IF EXISTS public.facilities_facility_id_seq;
DROP TABLE IF EXISTS public.facilities;
DROP SEQUENCE IF EXISTS public.bookings_booking_id_seq;
DROP TABLE IF EXISTS public.bookings;
DROP SEQUENCE IF EXISTS public.booking_history_history_id_seq;
DROP TABLE IF EXISTS public.booking_history;
DROP FUNCTION IF EXISTS public.set_updated_at();
DROP TYPE IF EXISTS public.room_type;
DROP TYPE IF EXISTS public.request_status;
DROP TYPE IF EXISTS public.facility_type;
DROP TYPE IF EXISTS public.booking_status;
DROP EXTENSION IF EXISTS btree_gist;
--
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;


--
-- Name: EXTENSION btree_gist; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION btree_gist IS 'support for indexing common datatypes in GiST';


--
-- Name: booking_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.booking_status AS ENUM (
    'CONFIRMED',
    'CANCELLED'
);


--
-- Name: facility_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.facility_type AS ENUM (
    'SAC_HALL',
    'GUEST_HOUSE',
    'CLH',
    'AUDITORIUM'
);


--
-- Name: request_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.request_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'CANCELLED'
);


--
-- Name: room_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.room_type AS ENUM (
    'SINGLE',
    'DOUBLE',
    'STANDARD'
);


--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: booking_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.booking_history (
    history_id bigint NOT NULL,
    entity_type text NOT NULL,
    entity_id bigint NOT NULL,
    action text NOT NULL,
    actor_name text NOT NULL,
    actor_roll_number text,
    actor_role text NOT NULL,
    old_data jsonb,
    new_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT booking_history_entity_type_check CHECK ((entity_type = ANY (ARRAY['BOOKING'::text, 'REQUEST'::text])))
);


--
-- Name: booking_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.booking_history_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: booking_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.booking_history_history_id_seq OWNED BY public.booking_history.history_id;


--
-- Name: bookings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bookings (
    booking_id bigint NOT NULL,
    room_id integer NOT NULL,
    booker_name text NOT NULL,
    booker_roll_number text,
    booker_role text NOT NULL,
    purpose text,
    booking_date date,
    start_hour integer,
    end_hour integer,
    check_in date,
    check_out date,
    status public.booking_status DEFAULT 'CONFIRMED'::public.booking_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT bookings_check CHECK ((((booking_date IS NOT NULL) AND (start_hour IS NOT NULL) AND (end_hour IS NOT NULL) AND (check_in IS NULL) AND (check_out IS NULL) AND (start_hour >= 0) AND (start_hour <= 23) AND (end_hour > start_hour) AND (end_hour <= 24)) OR ((booking_date IS NULL) AND (start_hour IS NULL) AND (end_hour IS NULL) AND (check_in IS NOT NULL) AND (check_out IS NOT NULL) AND (check_in < check_out))))
);


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bookings_booking_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bookings_booking_id_seq OWNED BY public.bookings.booking_id;


--
-- Name: facilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facilities (
    facility_id integer NOT NULL,
    name text NOT NULL,
    facility_type public.facility_type NOT NULL,
    active boolean DEFAULT true NOT NULL
);


--
-- Name: facilities_facility_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.facilities_facility_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: facilities_facility_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.facilities_facility_id_seq OWNED BY public.facilities.facility_id;


--
-- Name: requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.requests (
    request_id bigint NOT NULL,
    room_id integer NOT NULL,
    requester_name text NOT NULL,
    requester_roll_number text,
    requester_role text NOT NULL,
    purpose text,
    booking_date date,
    start_hour integer,
    end_hour integer,
    check_in date,
    check_out date,
    status public.request_status DEFAULT 'PENDING'::public.request_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    decided_at timestamp with time zone,
    decided_by_name text,
    decided_by_role text,
    CONSTRAINT requests_check CHECK ((((booking_date IS NOT NULL) AND (start_hour IS NOT NULL) AND (end_hour IS NOT NULL) AND (check_in IS NULL) AND (check_out IS NULL) AND (start_hour >= 0) AND (start_hour <= 23) AND (end_hour > start_hour) AND (end_hour <= 24)) OR ((booking_date IS NULL) AND (start_hour IS NULL) AND (end_hour IS NULL) AND (check_in IS NOT NULL) AND (check_out IS NOT NULL) AND (check_in < check_out))))
);


--
-- Name: requests_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.requests_request_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: requests_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.requests_request_id_seq OWNED BY public.requests.request_id;


--
-- Name: rooms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rooms (
    room_id integer NOT NULL,
    facility_id integer NOT NULL,
    room_code text NOT NULL,
    room_type public.room_type DEFAULT 'STANDARD'::public.room_type NOT NULL,
    price_per_day numeric(10,2),
    active boolean DEFAULT true NOT NULL
);


--
-- Name: rooms_room_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rooms_room_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rooms_room_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rooms_room_id_seq OWNED BY public.rooms.room_id;


--
-- Name: booking_history history_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booking_history ALTER COLUMN history_id SET DEFAULT nextval('public.booking_history_history_id_seq'::regclass);


--
-- Name: bookings booking_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings ALTER COLUMN booking_id SET DEFAULT nextval('public.bookings_booking_id_seq'::regclass);


--
-- Name: facilities facility_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilities ALTER COLUMN facility_id SET DEFAULT nextval('public.facilities_facility_id_seq'::regclass);


--
-- Name: requests request_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests ALTER COLUMN request_id SET DEFAULT nextval('public.requests_request_id_seq'::regclass);


--
-- Name: rooms room_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms ALTER COLUMN room_id SET DEFAULT nextval('public.rooms_room_id_seq'::regclass);


--
-- Data for Name: booking_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.booking_history (history_id, entity_type, entity_id, action, actor_name, actor_roll_number, actor_role, old_data, new_data, created_at) FROM stdin;
1	BOOKING	1	CREATED	Aarav Sharma	2501CS09	student	\N	{"status": "CONFIRMED", "purpose": "Academic", "room_id": 1, "check_in": null, "end_hour": 15, "check_out": null, "room_code": "SAC-HALL", "room_type": "STANDARD", "booking_id": 1, "created_at": "2026-09-15T20:53:52.014893+00:00", "start_hour": 14, "updated_at": "2026-09-15T20:53:52.014893+00:00", "booker_name": "Aarav Sharma", "booker_role": "student", "booking_date": "2026-09-17", "facility_name": "SAC Hall", "facility_type": "SAC_HALL", "price_per_day": null, "booker_roll_number": "2501CS09"}	2026-09-15 20:53:52.014893+00
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bookings (booking_id, room_id, booker_name, booker_roll_number, booker_role, purpose, booking_date, start_hour, end_hour, check_in, check_out, status, created_at, updated_at) FROM stdin;
1	1	Aarav Sharma	2501CS09	student	Academic	2026-09-17	14	15	\N	\N	CONFIRMED	2026-09-15 20:53:52.014893+00	2026-09-15 20:53:52.014893+00
\.


--
-- Data for Name: facilities; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.facilities (facility_id, name, facility_type, active) FROM stdin;
1	SAC Hall	SAC_HALL	t
2	Guest House	GUEST_HOUSE	t
3	CLH	CLH	t
4	Auditorium	AUDITORIUM	t
\.


--
-- Data for Name: requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.requests (request_id, room_id, requester_name, requester_roll_number, requester_role, purpose, booking_date, start_hour, end_hour, check_in, check_out, status, created_at, updated_at, decided_at, decided_by_name, decided_by_role) FROM stdin;
\.


--
-- Data for Name: rooms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rooms (room_id, facility_id, room_code, room_type, price_per_day, active) FROM stdin;
1	1	SAC-HALL	STANDARD	\N	t
2	2	GH-S-01	SINGLE	1200.00	t
3	2	GH-S-02	SINGLE	1200.00	t
4	2	GH-S-03	SINGLE	1200.00	t
5	2	GH-S-04	SINGLE	1200.00	t
6	2	GH-S-05	SINGLE	1200.00	t
7	2	GH-S-06	SINGLE	1200.00	t
8	2	GH-S-07	SINGLE	1200.00	t
9	2	GH-S-08	SINGLE	1200.00	t
10	2	GH-S-09	SINGLE	1200.00	t
11	2	GH-S-10	SINGLE	1200.00	t
12	2	GH-D-01	DOUBLE	1800.00	t
13	2	GH-D-02	DOUBLE	1800.00	t
14	2	GH-D-03	DOUBLE	1800.00	t
15	2	GH-D-04	DOUBLE	1800.00	t
16	2	GH-D-05	DOUBLE	1800.00	t
17	2	GH-D-06	DOUBLE	1800.00	t
18	2	GH-D-07	DOUBLE	1800.00	t
19	2	GH-D-08	DOUBLE	1800.00	t
20	2	GH-D-09	DOUBLE	1800.00	t
21	2	GH-D-10	DOUBLE	1800.00	t
22	3	CLH-01	STANDARD	\N	t
23	3	CLH-02	STANDARD	\N	t
24	3	CLH-03	STANDARD	\N	t
25	3	CLH-04	STANDARD	\N	t
26	3	CLH-05	STANDARD	\N	t
27	3	CLH-06	STANDARD	\N	t
28	4	AUDITORIUM	STANDARD	\N	t
\.


--
-- Name: booking_history_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.booking_history_history_id_seq', 1, true);


--
-- Name: bookings_booking_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.bookings_booking_id_seq', 1, true);


--
-- Name: facilities_facility_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.facilities_facility_id_seq', 4, true);


--
-- Name: requests_request_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.requests_request_id_seq', 1, false);


--
-- Name: rooms_room_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.rooms_room_id_seq', 28, true);


--
-- Name: booking_history booking_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.booking_history
    ADD CONSTRAINT booking_history_pkey PRIMARY KEY (history_id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (booking_id);


--
-- Name: facilities facilities_facility_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilities
    ADD CONSTRAINT facilities_facility_type_key UNIQUE (facility_type);


--
-- Name: facilities facilities_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilities
    ADD CONSTRAINT facilities_name_key UNIQUE (name);


--
-- Name: facilities facilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilities
    ADD CONSTRAINT facilities_pkey PRIMARY KEY (facility_id);


--
-- Name: bookings no_overlapping_daily_bookings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT no_overlapping_daily_bookings EXCLUDE USING gist (room_id WITH =, daterange(check_in, check_out, '[)'::text) WITH &&) WHERE (((status = 'CONFIRMED'::public.booking_status) AND (check_in IS NOT NULL)));


--
-- Name: bookings no_overlapping_hourly_bookings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT no_overlapping_hourly_bookings EXCLUDE USING gist (room_id WITH =, int8range(((((booking_date - '2000-01-01'::date))::bigint * 24) + start_hour), ((((booking_date - '2000-01-01'::date))::bigint * 24) + end_hour), '[)'::text) WITH &&) WHERE (((status = 'CONFIRMED'::public.booking_status) AND (booking_date IS NOT NULL)));


--
-- Name: requests requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_pkey PRIMARY KEY (request_id);


--
-- Name: rooms rooms_facility_id_room_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_facility_id_room_code_key UNIQUE (facility_id, room_code);


--
-- Name: rooms rooms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_pkey PRIMARY KEY (room_id);


--
-- Name: rooms rooms_room_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_room_code_key UNIQUE (room_code);


--
-- Name: idx_bookings_booker; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_booker ON public.bookings USING btree (booker_roll_number, booker_name);


--
-- Name: idx_bookings_guest_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_guest_dates ON public.bookings USING btree (room_id, check_in, check_out);


--
-- Name: idx_bookings_room_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bookings_room_date ON public.bookings USING btree (room_id, booking_date);


--
-- Name: idx_history_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_history_entity ON public.booking_history USING btree (entity_type, entity_id);


--
-- Name: idx_requests_requester; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_requests_requester ON public.requests USING btree (requester_roll_number, requester_name);


--
-- Name: idx_requests_room_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_requests_room_date ON public.requests USING btree (room_id, booking_date);


--
-- Name: idx_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_requests_status ON public.requests USING btree (status);


--
-- Name: bookings trg_bookings_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bookings_updated_at BEFORE UPDATE ON public.bookings FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: requests trg_requests_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_requests_updated_at BEFORE UPDATE ON public.requests FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: bookings bookings_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(room_id) ON DELETE RESTRICT;


--
-- Name: requests requests_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(room_id) ON DELETE RESTRICT;


--
-- Name: rooms rooms_facility_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_facility_id_fkey FOREIGN KEY (facility_id) REFERENCES public.facilities(facility_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict aTVG18a9Jbkbq9OcDvGdIYY8cUoe9It3GsUMgaCrmLhHgIGyPZddZZGGYJpKSr7


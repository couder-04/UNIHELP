--
-- PostgreSQL database dump
--

\restrict HXxxntGdwz1CQTNuNs9NPnmShPqjZSmxXxgw10ztrEl5Yj6Gg2x1wdHPQa35ill

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

DROP INDEX IF EXISTS public.idx_bus_schedule_start_dest;
DROP INDEX IF EXISTS public.idx_bus_schedule_day;
DROP INDEX IF EXISTS public.idx_bus_schedule_bus_name_lower;
DROP INDEX IF EXISTS public.idx_bus_schedule_bus_name;
ALTER TABLE IF EXISTS ONLY public.bus_schedule DROP CONSTRAINT IF EXISTS bus_schedule_pkey;
ALTER TABLE IF EXISTS public.bus_schedule ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.bus_schedule_id_seq;
DROP TABLE IF EXISTS public.bus_schedule;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bus_schedule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bus_schedule (
    id integer NOT NULL,
    day text NOT NULL,
    "time" time without time zone NOT NULL,
    bus_name text NOT NULL,
    start_point text NOT NULL,
    destination text NOT NULL,
    driver_name text,
    driver_no text
);


--
-- Name: bus_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bus_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bus_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bus_schedule_id_seq OWNED BY public.bus_schedule.id;


--
-- Name: bus_schedule id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bus_schedule ALTER COLUMN id SET DEFAULT nextval('public.bus_schedule_id_seq'::regclass);


--
-- Data for Name: bus_schedule; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.bus_schedule (id, day, "time", bus_name, start_point, destination, driver_name, driver_no) FROM stdin;
1	Monday	08:00:00	Bus 02	Aryabhatta	Tut Block	Ramesh Kumar	9876500002
2	Monday	08:15:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
3	Monday	17:30:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
4	Monday	17:45:00	Bus 02	Tut Block	Aryabhatta	Ramesh Kumar	9876500002
5	Tuesday	08:00:00	Bus 02	Aryabhatta	Tut Block	Ramesh Kumar	9876500002
6	Tuesday	08:15:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
7	Tuesday	17:30:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
8	Wednesday	08:00:00	Bus 02	Aryabhatta	Tut Block	Ramesh Kumar	9876500002
9	Wednesday	08:15:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
10	Wednesday	17:30:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
11	Thursday	08:00:00	Bus 02	Aryabhatta	Tut Block	Ramesh Kumar	9876500002
12	Thursday	17:30:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
13	Friday	08:00:00	Bus 02	Aryabhatta	Tut Block	Ramesh Kumar	9876500002
14	Friday	17:30:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
15	Saturday	09:00:00	Bus 02	Aryabhatta	Tut Block	Suresh Singh	9876500003
16	Saturday	18:00:00	Bus 02	Tut Block	Aryabhatta	Suresh Singh	9876500003
17	Sunday	10:00:00	Bus 02	Kalam	Tut Block	Suresh Singh	9876500003
18	Sunday	18:00:00	Bus 02	Tut Block	Kalam	Suresh Singh	9876500003
19	Monday	08:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
20	Monday	17:15:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
21	Monday	07:45:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
22	Monday	08:05:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
23	Monday	12:30:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
24	Monday	13:15:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
25	Monday	17:00:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
26	Monday	17:40:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
27	Tuesday	07:45:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
28	Tuesday	08:05:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
29	Tuesday	12:30:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
30	Tuesday	13:15:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
31	Tuesday	17:00:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
32	Tuesday	17:40:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
33	Wednesday	07:45:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
34	Wednesday	08:05:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
35	Wednesday	12:30:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
36	Wednesday	13:15:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
37	Wednesday	17:00:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
38	Wednesday	17:40:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
39	Thursday	07:45:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
40	Thursday	08:05:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
41	Thursday	12:30:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
42	Thursday	13:15:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
43	Thursday	17:00:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
44	Thursday	17:40:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
45	Friday	07:45:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
46	Friday	08:05:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
47	Friday	12:30:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
48	Friday	13:15:00	Bus 01	Asima	Tut Block	Priya Das	9876500001
49	Friday	17:00:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
50	Friday	17:40:00	Bus 01	Tut Block	Asima	Priya Das	9876500001
51	Monday	12:40:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
52	Monday	13:10:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
53	Tuesday	12:40:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
54	Tuesday	13:10:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
55	Tuesday	17:45:00	Bus 02	Tut Block	Aryabhatta	Ramesh Kumar	9876500002
56	Wednesday	12:40:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
57	Wednesday	13:10:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
58	Wednesday	17:45:00	Bus 02	Tut Block	Aryabhatta	Ramesh Kumar	9876500002
59	Thursday	08:15:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
60	Thursday	12:40:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
61	Thursday	13:10:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
62	Thursday	17:45:00	Bus 02	Tut Block	Aryabhatta	Ramesh Kumar	9876500002
63	Friday	08:15:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
64	Friday	12:40:00	Bus 02	Tut Block	Kalam	Ramesh Kumar	9876500002
65	Friday	13:10:00	Bus 02	Kalam	Tut Block	Ramesh Kumar	9876500002
66	Friday	17:45:00	Bus 02	Tut Block	Aryabhatta	Ramesh Kumar	9876500002
67	Monday	07:50:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
68	Monday	08:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
69	Monday	12:35:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
70	Monday	13:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
71	Monday	17:10:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
72	Monday	18:00:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
73	Tuesday	07:50:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
74	Tuesday	08:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
75	Tuesday	12:35:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
76	Tuesday	13:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
77	Tuesday	17:10:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
78	Tuesday	18:00:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
79	Wednesday	07:50:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
80	Wednesday	08:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
81	Wednesday	12:35:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
82	Wednesday	13:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
83	Wednesday	17:10:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
84	Wednesday	18:00:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
85	Thursday	07:50:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
86	Thursday	08:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
87	Thursday	12:35:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
88	Thursday	13:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
89	Thursday	17:10:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
90	Thursday	18:00:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
91	Friday	07:50:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
92	Friday	08:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
93	Friday	12:35:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
94	Friday	13:20:00	Bus 03	Kalam	Tut Block	Farooq Ali	9876500006
95	Friday	17:10:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
96	Friday	18:00:00	Bus 03	Tut Block	Kalam	Farooq Ali	9876500006
97	Monday	07:40:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
98	Monday	08:10:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
99	Monday	12:45:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
100	Monday	13:25:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
101	Monday	17:05:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
102	Monday	17:50:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
103	Tuesday	07:40:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
104	Tuesday	08:10:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
105	Tuesday	12:45:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
106	Tuesday	13:25:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
107	Tuesday	17:05:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
108	Tuesday	17:50:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
109	Wednesday	07:40:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
110	Wednesday	08:10:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
111	Wednesday	12:45:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
112	Wednesday	13:25:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
113	Wednesday	17:05:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
114	Wednesday	17:50:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
115	Thursday	07:40:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
116	Thursday	08:10:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
117	Thursday	12:45:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
118	Thursday	13:25:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
119	Thursday	17:05:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
120	Thursday	17:50:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
121	Friday	07:40:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
122	Friday	08:10:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
123	Friday	12:45:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
124	Friday	13:25:00	Bus 04	Aryabhatta	Tut Block	Kavita Nair	9876500004
125	Friday	17:05:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
126	Friday	17:50:00	Bus 04	Tut Block	Aryabhatta	Kavita Nair	9876500004
127	Monday	07:55:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
128	Monday	12:50:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
129	Monday	13:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
130	Monday	18:10:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
131	Tuesday	07:55:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
132	Tuesday	08:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
133	Tuesday	12:50:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
134	Tuesday	13:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
135	Tuesday	17:15:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
136	Tuesday	18:10:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
137	Wednesday	07:55:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
138	Wednesday	08:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
139	Wednesday	12:50:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
140	Wednesday	13:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
141	Wednesday	17:15:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
142	Wednesday	18:10:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
143	Thursday	07:55:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
144	Thursday	08:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
145	Thursday	12:50:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
146	Thursday	13:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
147	Thursday	17:15:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
148	Thursday	18:10:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
149	Friday	07:55:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
150	Friday	08:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
151	Friday	12:50:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
152	Friday	13:30:00	Bus 05	CV Raman	Tut Block	Anil Yadav	9876500005
153	Friday	17:15:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
154	Friday	18:10:00	Bus 05	Tut Block	CV Raman	Anil Yadav	9876500005
\.


--
-- Name: bus_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.bus_schedule_id_seq', 154, true);


--
-- Name: bus_schedule bus_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bus_schedule
    ADD CONSTRAINT bus_schedule_pkey PRIMARY KEY (id);


--
-- Name: idx_bus_schedule_bus_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bus_schedule_bus_name ON public.bus_schedule USING btree (bus_name);


--
-- Name: idx_bus_schedule_bus_name_lower; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bus_schedule_bus_name_lower ON public.bus_schedule USING btree (lower(bus_name));


--
-- Name: idx_bus_schedule_day; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bus_schedule_day ON public.bus_schedule USING btree (day);


--
-- Name: idx_bus_schedule_start_dest; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bus_schedule_start_dest ON public.bus_schedule USING btree (start_point, destination);


--
-- PostgreSQL database dump complete
--

\unrestrict HXxxntGdwz1CQTNuNs9NPnmShPqjZSmxXxgw10ztrEl5Yj6Gg2x1wdHPQa35ill


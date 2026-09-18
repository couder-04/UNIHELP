--
-- PostgreSQL database dump
--

\restrict P6WfU0GGL0kIOgPwNySh5JiN47Sdt7p5QMG6hEiCdanQELe4QrU5yH3WzCqSagH

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

DROP INDEX IF EXISTS public.idx_temporary_hostel_day;
DROP INDEX IF EXISTS public.idx_permanent_hostel_day;
ALTER TABLE IF EXISTS ONLY public.temporary DROP CONSTRAINT IF EXISTS temporary_pkey;
ALTER TABLE IF EXISTS ONLY public.permanent DROP CONSTRAINT IF EXISTS permanent_pkey;
DROP TABLE IF EXISTS public.temporary;
DROP TABLE IF EXISTS public.permanent;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: permanent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permanent (
    hostel text NOT NULL,
    day text NOT NULL,
    breakfast text,
    lunch text,
    snacks text,
    dinner text
);


--
-- Name: temporary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.temporary (
    hostel text NOT NULL,
    day text NOT NULL,
    breakfast text,
    lunch text,
    snacks text,
    dinner text
);


--
-- Data for Name: permanent; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permanent (hostel, day, breakfast, lunch, snacks, dinner) FROM stdin;
Kalam	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
Kalam	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
Kalam	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
Kalam	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
Kalam	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
Kalam	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
Kalam	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
Aryabhatta	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
Aryabhatta	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
Aryabhatta	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
Aryabhatta	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
Aryabhatta	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
Aryabhatta	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
Aryabhatta	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
CV Raman	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
CV Raman	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
CV Raman	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
CV Raman	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
CV Raman	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
CV Raman	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
CV Raman	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
Asima	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
Asima	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
Asima	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
Asima	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
Asima	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
Asima	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
Asima	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
\.


--
-- Data for Name: temporary; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.temporary (hostel, day, breakfast, lunch, snacks, dinner) FROM stdin;
Kalam	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
Kalam	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
Kalam	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
Kalam	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
Kalam	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
Kalam	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
Aryabhatta	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
Aryabhatta	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
Aryabhatta	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
Aryabhatta	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
Aryabhatta	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
Aryabhatta	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
Aryabhatta	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
CV Raman	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
CV Raman	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
CV Raman	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
CV Raman	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
CV Raman	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
CV Raman	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
CV Raman	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
Asima	Monday	Poha, banana, tea	Rice, dal, mixed veg, roti	Samosa, tea	Roti, dal, paneer, rice
Asima	Tuesday	Idli, sambar, coffee	Jeera rice, chole, salad	Bhel, lemonade	Roti, palak paneer, rice
Asima	Wednesday	Paratha, curd, tea	Rice, sambar, cabbage, roti	Pakora, tea	Roti, egg curry, rice
Asima	Thursday	Upma, fruit, tea	Rice, rajma, beans, roti	Sandwich, juice	Roti, chicken curry, rice
Asima	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
Asima	Saturday	Aloo paratha, pickle, tea	Rice, kadhi, aloo gobi, roti	Noodles, tea	Roti, mix veg, rice
Asima	Sunday	Chole bhature, tea	Veg biryani, raita, papad	Cake, coffee	Roti, malai kofta, rice
Kalam	Friday	Bread omelette, tea	Fried rice, dal tadka, roti	Vada, coffee	Roti, fish curry, rice
\.


--
-- Name: permanent permanent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permanent
    ADD CONSTRAINT permanent_pkey PRIMARY KEY (hostel, day);


--
-- Name: temporary temporary_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.temporary
    ADD CONSTRAINT temporary_pkey PRIMARY KEY (hostel, day);


--
-- Name: idx_permanent_hostel_day; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_permanent_hostel_day ON public.permanent USING btree (lower(hostel), lower(day));


--
-- Name: idx_temporary_hostel_day; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_temporary_hostel_day ON public.temporary USING btree (lower(hostel), lower(day));


--
-- PostgreSQL database dump complete
--

\unrestrict P6WfU0GGL0kIOgPwNySh5JiN47Sdt7p5QMG6hEiCdanQELe4QrU5yH3WzCqSagH


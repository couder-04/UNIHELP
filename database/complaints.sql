--
-- PostgreSQL database dump
--

\restrict GOoOLfiqxltfWuRe0ANC6ST8D1ADhONaz2mn43tG5VtdaYO46jAAINcEiJSzID0

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

ALTER TABLE IF EXISTS ONLY public.complaints DROP CONSTRAINT IF EXISTS complaints_verified_by_fkey;
ALTER TABLE IF EXISTS ONLY public.complaints DROP CONSTRAINT IF EXISTS complaints_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.complaints DROP CONSTRAINT IF EXISTS complaints_completed_by_fkey;
ALTER TABLE IF EXISTS ONLY public.complaint_history DROP CONSTRAINT IF EXISTS complaint_history_complaint_id_fkey;
ALTER TABLE IF EXISTS ONLY public.complaint_history DROP CONSTRAINT IF EXISTS complaint_history_actor_id_fkey;
DROP TRIGGER IF EXISTS trg_users_roll_number_to_id ON public.users;
DROP TRIGGER IF EXISTS trg_prune_completed_complaints ON public.complaints;
DROP INDEX IF EXISTS public.uniq_open_complaints;
DROP INDEX IF EXISTS public.idx_complaints_user_id;
DROP INDEX IF EXISTS public.idx_complaints_status;
DROP INDEX IF EXISTS public.idx_complaints_created_at;
DROP INDEX IF EXISTS public.idx_complaints_category_completed;
DROP INDEX IF EXISTS public.idx_complaints_category;
DROP INDEX IF EXISTS public.idx_complaint_history_complaint_id;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_roll_number_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.complaints DROP CONSTRAINT IF EXISTS complaints_pkey;
ALTER TABLE IF EXISTS ONLY public.complaints DROP CONSTRAINT IF EXISTS complaints_complaint_number_key;
ALTER TABLE IF EXISTS ONLY public.complaint_history DROP CONSTRAINT IF EXISTS complaint_history_pkey;
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.complaints;
DROP TABLE IF EXISTS public.complaint_history;
DROP FUNCTION IF EXISTS public.users_set_roll_number_to_id();
DROP FUNCTION IF EXISTS public.prune_old_completed_complaints();
DROP EXTENSION IF EXISTS pgcrypto;
--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: prune_old_completed_complaints(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.prune_old_completed_complaints() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM complaints
    WHERE LOWER(category) = LOWER(NEW.category)
      AND status = 'COMPLETED'
      AND id NOT IN (
          SELECT id
          FROM complaints
          WHERE LOWER(category) = LOWER(NEW.category)
            AND status = 'COMPLETED'
          ORDER BY completed_at DESC NULLS LAST, created_at DESC
          LIMIT 50
      );
    RETURN NEW;
END;
$$;


--
-- Name: users_set_roll_number_to_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.users_set_roll_number_to_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.id IS NULL OR btrim(NEW.id) = '' THEN
        NEW.id := NEW.roll_number;
    END IF;
    IF NEW.roll_number IS NULL OR btrim(NEW.roll_number) = '' THEN
        NEW.roll_number := NEW.id;
    END IF;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: complaint_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaint_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    complaint_id uuid NOT NULL,
    actor_id text,
    actor_role character varying NOT NULL,
    action character varying NOT NULL,
    from_status character varying,
    to_status character varying,
    extra json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: complaints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.complaints (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    complaint_number character varying(32) NOT NULL,
    user_id text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    category character varying(20) NOT NULL,
    status character varying(32) DEFAULT 'PENDING_VERIFICATION'::character varying NOT NULL,
    verified_by text,
    verified_at timestamp with time zone,
    completed_by text,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    name text,
    roll_number text,
    CONSTRAINT complaints_category_check CHECK ((lower((category)::text) = ANY (ARRAY['academic'::text, 'hostel'::text, 'mess'::text]))),
    CONSTRAINT complaints_description_check CHECK ((btrim(description) <> ''::text)),
    CONSTRAINT complaints_status_check CHECK (((status)::text = ANY ((ARRAY['PENDING_VERIFICATION'::character varying, 'PROGRESS'::character varying, 'COMPLETED'::character varying])::text[]))),
    CONSTRAINT complaints_title_check CHECK ((btrim(title) <> ''::text))
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id text NOT NULL,
    authentication_key character varying,
    role character varying,
    names text,
    roll_number text,
    email character varying,
    created_at timestamp with time zone DEFAULT now(),
    hierarchy_level character varying,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT users_roll_number_eq_id CHECK ((roll_number = id))
);


--
-- Data for Name: complaint_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.complaint_history (id, complaint_id, actor_id, actor_role, action, from_status, to_status, extra, created_at) FROM stdin;
402c6cc2-ff01-4023-ad66-5efec54f48da	eecc4054-7ef0-49a5-9cf2-ec99b4b63088	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "hostel"}	2026-09-15 20:36:44.669075+00
1df14dd5-7eba-463f-a59b-3273b0331724	04771f4f-616b-48c7-bb14-b134de840aa1	PF001	Faculty	complaint_created	\N	PENDING_VERIFICATION	{"category": "hostel"}	2026-09-15 20:37:41.802657+00
36f0894f-bc9d-485a-bdb6-fbc88c2ccd08	04771f4f-616b-48c7-bb14-b134de840aa1	PF001	Faculty	complaint_verified	PENDING_VERIFICATION	PROGRESS	\N	2026-09-15 20:37:48.074239+00
d6b437a8-588b-47e9-ac77-c283a31326fb	eecc4054-7ef0-49a5-9cf2-ec99b4b63088	PF001	Faculty	complaint_verified	PENDING_VERIFICATION	PROGRESS	\N	2026-09-15 20:40:46.907163+00
3df03130-de71-4f08-939f-ab2a5dfd4618	60695d28-7085-4092-b2ca-e1354fbdad33	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "hostel"}	2026-09-18 12:42:48.5991+00
3d5dd47b-5687-4c53-856e-6a3d5ebef518	cba1bb9c-1632-48df-ad6b-c2d6dd363a87	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "hostel"}	2026-09-18 12:56:52.133616+00
c0c0af5a-97b7-4425-b22d-9176706d6609	9d741ae4-4592-460e-ae1d-d32e025ea7d2	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 13:38:27.682525+00
aa2827f7-07ad-44bc-8a90-fa42c71c43f4	761b7693-9ae6-4cac-a5ee-3efdb9ed10a8	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 13:38:33.927853+00
3c34b98e-5edb-490b-a2f5-43f7fc1b9c64	7b91cfaa-991f-4a76-80bc-c9e8cba4269f	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 13:38:39.959085+00
9d92b14a-4699-46af-825e-3b234ada3123	d6b9ef4b-cd01-4ee6-9fc5-cddcd089066a	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 14:34:28.937838+00
34e3c67a-9b6b-4cec-9cc0-dc1b67df1aa4	ce76703c-7d80-4c0f-8adb-74b40152f559	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 14:34:33.694998+00
173720ac-4bd0-4be2-990b-d46610d18e20	8cf101a1-bf15-426c-b648-72fc0bfb2364	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 14:34:39.698087+00
c9bd5050-9f15-4060-b8ac-019bed9ae330	29591ef0-799c-4b9a-b27a-c0f27f9aef18	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 14:44:55.321611+00
3c2b0051-9c9a-4515-bbd9-917c071c2345	badac580-9660-4897-99c0-2d7cbaf7d092	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 14:45:00.679832+00
4bd2c46b-8696-4d72-a948-51e3deaf33e4	bfff4b30-86ae-4a5b-960b-cff8a79e9f27	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "mess"}	2026-09-18 14:45:20.305909+00
5c4347a9-99c3-46f6-a310-eb682d0cc1f9	037769de-ea91-4aa7-a2e9-d2629e17c73b	2501CS09	Student	complaint_created	\N	PENDING_VERIFICATION	{"category": "hostel"}	2026-09-18 14:55:45.418043+00
\.


--
-- Data for Name: complaints; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.complaints (id, complaint_number, user_id, title, description, category, status, verified_by, verified_at, completed_by, completed_at, created_at, updated_at, name, roll_number) FROM stdin;
eecc4054-7ef0-49a5-9cf2-ec99b4b63088	C-695483	2501CS09	Broken water cooler on floor	The water cooler on my floor is broken	hostel	PROGRESS	PF001	2026-09-15 20:40:46.907163+00	\N	\N	2026-09-15 20:36:44.669075+00	2026-09-15 20:40:46.907163+00	Aarav Sharma	2501CS09
04771f4f-616b-48c7-bb14-b134de840aa1	C-541267	PF001	Broken water cooler on Kalam floor 2	The water cooler on Kalam floor 2 is broken and not working.	hostel	PROGRESS	PF001	2026-09-15 20:37:48.074239+00	\N	\N	2026-09-15 20:37:41.802657+00	2026-09-15 20:37:48.074239+00	Priya Patel	PF001
60695d28-7085-4092-b2ca-e1354fbdad33	C-606640	2501CS09	Water cooler broken on floor	The water cooler on my floor is broken and not working.	hostel	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 12:42:48.5991+00	2026-09-18 12:42:48.5991+00	Aarav Sharma	2501CS09
cba1bb9c-1632-48df-ad6b-c2d6dd363a87	C-199538	2501CS09	Water cooler not working on floor	The water cooler on my hostel floor is broken and not dispensing water.	hostel	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 12:56:52.133616+00	2026-09-18 12:56:52.133616+00	Aarav Sharma	2501CS09
9d741ae4-4592-460e-ae1d-d32e025ea7d2	C-075413	2501CS09	Mess food quality was bad today	The food served in the mess today was of poor quality — not up to the usual standard. Please look into it.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 13:38:27.682525+00	2026-09-18 13:38:27.682525+00	Aarav Sharma	2501CS09
761b7693-9ae6-4cac-a5ee-3efdb9ed10a8	C-851979	2501CS09	Poor mess food quality	The food served in the mess today was of poor quality. Requesting the mess committee to look into the issue and improve the quality of food served.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 13:38:33.927853+00	2026-09-18 13:38:33.927853+00	Aarav Sharma	2501CS09
7b91cfaa-991f-4a76-80bc-c9e8cba4269f	C-151771	2501CS09	Poor mess food quality today	The food served in the mess today was of poor quality and not up to the expected standard. Requesting the mess authorities to look into this.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 13:38:39.959085+00	2026-09-18 13:38:39.959085+00	Aarav Sharma	2501CS09
d6b9ef4b-cd01-4ee6-9fc5-cddcd089066a	C-564468	2501CS09	Poor mess food quality today	The mess food quality was bad today. The food was not up to the usual standard and needs to be looked into.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 14:34:28.937838+00	2026-09-18 14:34:28.937838+00	Aarav Sharma	2501CS09
ce76703c-7d80-4c0f-8adb-74b40152f559	C-223637	2501CS09	Poor food quality today	The food quality in the mess today was bad and not up to the usual standard.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 14:34:33.694998+00	2026-09-18 14:34:33.694998+00	Aarav Sharma	2501CS09
8cf101a1-bf15-426c-b648-72fc0bfb2364	C-936656	2501CS09	Poor mess food quality today	The food served in the mess today was of poor quality. Requesting the mess committee to look into the issue.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 14:34:39.698087+00	2026-09-18 14:34:39.698087+00	Aarav Sharma	2501CS09
29591ef0-799c-4b9a-b27a-c0f27f9aef18	C-632299	2501CS09	Poor mess food quality today	The food quality in the mess was bad today. The taste and freshness of the food were below acceptable standards, and the overall quality needs improvement.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 14:44:55.321611+00	2026-09-18 14:44:55.321611+00	Aarav Sharma	2501CS09
badac580-9660-4897-99c0-2d7cbaf7d092	C-907489	2501CS09	Poor mess food quality today	The mess food quality was bad today and needs to be looked into.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 14:45:00.679832+00	2026-09-18 14:45:00.679832+00	Aarav Sharma	2501CS09
bfff4b30-86ae-4a5b-960b-cff8a79e9f27	C-989010	2501CS09	Poor mess food quality today	The quality of food served in the mess today was very bad. Requesting the mess committee to look into the quality and hygiene of the food being served.	mess	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 14:45:20.305909+00	2026-09-18 14:45:20.305909+00	Aarav Sharma	2501CS09
037769de-ea91-4aa7-a2e9-d2629e17c73b	C-953189	2501CS09	Water cooler broken on floor	The water cooler on my floor is broken and not dispensing water.	hostel	PENDING_VERIFICATION	\N	\N	\N	\N	2026-09-18 14:55:45.418043+00	2026-09-18 14:55:45.418043+00	Aarav Sharma	2501CS09
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, authentication_key, role, names, roll_number, email, created_at, hierarchy_level, is_active) FROM stdin;
2501CB01	student-j	student	J Samrutha	2501CB01	2501cb01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB02	student-priyanshi	student	Priyanshi Patel	2501CB02	2501cb02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB03	student-dia	student	Dia Halder	2501CB03	2501cb03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB04	student-emin	student	Emin Philip Saji	2501CB04	2501cb04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB05	student-kajal	student	Kajal Batra	2501CB05	2501cb05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB06	student-archit	student	Archit Shanker	2501CB06	2501cb06@example.edu	2026-09-15 21:22:50.747212+00	student	t
PF001	faculty-demo	faculty	Priya Patel	PF001	priya.patel@example.edu	2026-09-15 20:09:57.181405+00	faculty	t
AD001	admin-demo	admin	Rohan Verma	AD001	rohan.verma@example.edu	2026-09-15 20:09:57.181405+00	admin	t
2501CB07	student-jarpula	student	Jarpula Murali	2501CB07	2501cb07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB08	student-manav	student	Manav Rathore	2501CB08	2501cb08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501AI51	student-ananya	student	Ananya Iyer	2501AI51	ananya.iyer@example.edu	2026-09-15 21:01:15.329747+00	student	t
2501CB09	student-saptarshi	student	Saptarshi Bose	2501CB09	2501cb09@example.edu	2026-09-15 21:22:50.747212+00	student	t
PF002	faculty-arjun	faculty	Arjun Nair	PF002	arjun.nair@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF003	faculty-meera	faculty	Meera Joshi	PF003	meera.joshi@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF004	faculty-sameer	faculty	Sameer Khan	PF004	sameer.khan@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF005	faculty-kavita	faculty	Kavita Desai	PF005	kavita.desai@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF006	faculty-aditi	faculty	Aditi Rao	PF006	aditi.rao@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF007	faculty-harsh	faculty	Harsh Vardhan	PF007	harsh.vardhan@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF008	faculty-leela	faculty	Leela Menon	PF008	leela.menon@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF009	faculty-omar	faculty	Omar Qureshi	PF009	omar.qureshi@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF010	faculty-tanvi	faculty	Tanvi Shah	PF010	tanvi.shah@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF011	faculty-nikhil	faculty	Nikhil Rao	PF011	nikhil.rao@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF012	faculty-pooja	faculty	Pooja Bhatt	PF012	pooja.bhatt@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF013	faculty-farhan	faculty	Farhan Ali	PF013	farhan.ali@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF014	faculty-diya	faculty	Diya Kulkarni	PF014	diya.kulkarni@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF015	faculty-yash	faculty	Yash Agarwal	PF015	yash.agarwal@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
PF016	faculty-sana	faculty	Sana Iqbal	PF016	sana.iqbal@example.edu	2026-09-15 21:01:15.329747+00	faculty	t
AD002	admin-nisha	admin	Nisha Kapoor	AD002	nisha.kapoor@example.edu	2026-09-15 21:01:15.329747+00	admin	t
2501CB10	student-katuri	student	Katuri Vanshika	2501CB10	2501cb10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB17	student-vaibhav	student	Vaibhav Sanjay Bhagure	2501CB17	2501cb17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB18	student-vansh	student	Vansh Khurana	2501CB18	2501cb18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB19	student-dhruv	student	Dhruv Agnihotri	2501CB19	2501cb19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB20	student-oshi	student	Oshi Malviya	2501CB20	2501cb20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB21	student-nasreen	student	Nasreen Fatima	2501CB21	2501cb21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB22	student-dhruv-ganatra	student	Dhruv Arvind Ganatra	2501CB22	2501cb22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB23	student-aarsh	student	Aarsh Jain	2501CB23	2501cb23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB24	student-dhadse	student	Dhadse Omesh Vasantrao	2501CB24	2501cb24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB25	student-vaanya	student	Vaanya Verma	2501CB25	2501cb25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB26	student-aryan	student	Aryan Dev	2501CB26	2501cb26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB27	student-vaishnav	student	Vaishnav Krishna Durgasi	2501CB27	2501cb27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB28	student-shantanu	student	Shantanu Sardar	2501CB28	2501cb28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB29	student-kavya	student	Kavya Gupta	2501CB29	2501cb29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB30	student-swarnava	student	Swarnava Kundu	2501CB30	2501cb30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB31	student-hemant	student	Hemant Kumar Bairwa	2501CB31	2501cb31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB32	student-biki	student	Biki Barman	2501CB32	2501cb32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB33	student-abhishek	student	Abhishek Bansal	2501CB33	2501cb33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB34	student-anser	student	Anser Ayaan	2501CB34	2501cb34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB35	student-s	student	S Aditya	2501CB35	2501cb35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB36	student-vadavelli	student	Vadavelli Kamali Harshitha	2501CB36	2501cb36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB37	student-anupam	student	Anupam Sharma	2501CB37	2501cb37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB38	student-sai	student	Sai Subrat Jena	2501CB38	2501cb38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB39	student-aman	student	Aman Saroj	2501CB39	2501cb39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB40	student-gaurav	student	Gaurav Sukhadia	2501CB40	2501cb40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB41	student-avdhesh	student	Avdhesh Meena	2501CB41	2501cb41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB42	student-ahan	student	Ahan Bhattacharjee	2501CB42	2501cb42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB43	student-madhur	student	Madhur Srivastava	2501CB43	2501cb43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB44	student-sakala	student	Sakala Sathwik	2501CB44	2501cb44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB45	student-pilli	student	Pilli Sri Vaishnavi	2501CB45	2501cb45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB46	student-chilmakuri	student	Chilmakuri Charan	2501CB46	2501cb46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB47	student-hariom	student	Hariom Singh	2501CB47	2501cb47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB48	student-mada	student	Mada Akeera Sri Varshan	2501CB48	2501cb48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB49	student-abhi	student	Abhi Raj	2501CB49	2501cb49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB50	student-raushan	student	Raushan Kumar	2501CB50	2501cb50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB51	student-boyina	student	Boyina Sadvika	2501CB51	2501cb51@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB52	student-sarthak	student	Sarthak Anusimi	2501CB52	2501cb52@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB53	student-sanket	student	Sanket Yadav Jadhav	2501CB53	2501cb53@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB54	student-riddhi	student	Riddhi Patel	2501CB54	2501cb54@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB55	student-sachin	student	Sachin	2501CB55	2501cb55@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB56	student-raj	student	Raj Aryan	2501CB56	2501cb56@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB57	student-raghvendra	student	Raghvendra Meena	2501CB57	2501cb57@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB58	student-adwait	student	Adwait Vats	2501CB58	2501cb58@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB59	student-snehadip	student	Snehadip Ghosh	2501CB59	2501cb59@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB60	student-biswas	student	Biswas Mayank Pradyut	2501CB60	2501cb60@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB61	student-satish	student	Satish Kumar Yadav	2501CB61	2501cb61@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB62	student-anshu	student	Anshu Vishwakarma	2501CB62	2501cb62@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB63	student-taniya	student	Taniya Kumari Gupta	2501CB63	2501cb63@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB64	student-shorya	student	Shorya Pratap Singh	2501CB64	2501cb64@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB65	student-vadithya	student	Vadithya Upendar	2501CB65	2501cb65@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS01	student-peruru	student	Peruru Snigdha Reddy	2501CS01	2501cs01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS02	student-kummara	student	Kummara Jyothi Prajwal	2501CS02	2501cs02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS03	student-choudavarapu	student	Choudavarapu Snehan	2501CS03	2501cs03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS04	student-megh	student	Megh Dhaval Parikh	2501CS04	2501cs04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS05	student-pranjal	student	Pranjal Kukreja	2501CS05	2501cs05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS06	student-tata	student	Tata Jayanth Naga Sai	2501CS06	2501cs06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS07	student-aayush	student	Aayush Raj	2501CS07	2501cs07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS08	student-ritesh	student	Ritesh	2501CS08	2501cs08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS09	student-demo	student	Aarav Sharma	2501CS09	2501cs09@example.edu	2026-09-15 20:09:57.181405+00	student	t
2501CS10	student-shushant	student	Shushant	2501CS10	2501cs10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS11	student-bhukya	student	Bhukya Pavan Kumar	2501CS11	2501cs11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS12	student-manish	student	Manish Sharma	2501CS12	2501cs12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS13	student-shreya	student	Shreya Kumari	2501CS13	2501cs13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS14	student-keshav	student	Keshav Jha	2501CS14	2501cs14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS15	student-chitra	student	Chitra Sandilya	2501CS15	2501cs15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603AI04	student-muskan	student	Muskan sharma	2603AI04	2603ai04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS16	student-sachin-gautam	student	Sachin Gautam	2501CS16	2501cs16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS17	student-prashant	student	Prashant Kumar	2501CS17	2501cs17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS18	student-sabavath	student	Sabavath Aishwarya Chouhan	2501CS18	2501cs18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS19	student-aditya	student	Aditya Kumar	2501CS19	2501cs19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS20	student-ayush	student	Ayush Anand	2501CS20	2501cs20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS21	student-shristi	student	Shristi Kumari	2501CS21	2501cs21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS22	student-vijayanagaram	student	Vijayanagaram Sreethi	2501CS22	2501cs22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS23	student-suzal	student	Suzal	2501CS23	2501cs23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS24	student-parth	student	Parth Tomar	2501CS24	2501cs24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS25	student-kotollu	student	Kotollu Neharika	2501CS25	2501cs25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS26	student-gaurav-choudhury	student	Gaurav Choudhury	2501CS26	2501cs26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS27	student-bartika	student	Bartika Kumar	2501CS27	2501cs27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS28	student-gunturu	student	Gunturu Srikanth	2501CS28	2501cs28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS29	student-pola	student	Pola Hymavathi	2501CS29	2501cs29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS30	student-affan	student	Affan Mushtaque	2501CS30	2501cs30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS31	student-jangiti	student	Jangiti Sathwik Kumar	2501CS31	2501cs31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS32	student-anushtup	student	Anushtup Kumar	2501CS32	2501cs32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS33	student-gandhe	student	Gandhe Sahasra	2501CS33	2501cs33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS34	student-anushka	student	Anushka Nayak	2501CS34	2501cs34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS35	student-rajiv	student	Rajiv Kumar Karn	2501CS35	2501cs35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS36	student-abhirup	student	Abhirup Dhara	2501CS36	2501cs36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS37	student-akshay	student	Akshay Kulkarni	2501CS37	2501cs37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS38	student-jakkula	student	Jakkula Udayasree	2501CS38	2501cs38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS39	student-harshil	student	Harshil Chukkala	2501CS39	2501cs39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS40	student-anuj	student	Anuj Omprakash Pupal	2501CS40	2501cs40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS41	student-mekala	student	Mekala Uday Kiran	2501CS41	2501cs41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS42	student-shivam	student	Shivam Kapoor	2501CS42	2501cs42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS43	student-kasireddy	student	Kasireddy Sri Charan	2501CS43	2501cs43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS44	student-aryan-kumar	student	Aryan Kumar	2501CS44	2501cs44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS45	student-guguloth	student	Guguloth Arun	2501CS45	2501cs45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS46	student-pranay	student	Pranay Bansal	2501CS46	2501cs46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS47	student-somu	student	Somu Nitin Deeraj Anja	2501CS47	2501cs47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS48	student-bikesh	student	Bikesh Loonaich	2501CS48	2501cs48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS49	student-mukka	student	Mukka Anjani Koumudh	2501CS49	2501cs49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS50	student-chinthareddy	student	Chinthareddy Varun Te	2501CS50	2501cs50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS51	student-ojasvee	student	Ojasvee Vatsa	2501CS51	2501cs51@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS52	student-aman-gautam	student	Aman Gautam	2501CS52	2501cs52@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS53	student-yash	student	Yash Trivedi	2501CS53	2501cs53@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS54	student-gade	student	Gade Chandan	2501CS54	2501cs54@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS55	student-bedabrata	student	Bedabrata Ghosh	2501CS55	2501cs55@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS56	student-pinakpani	student	Pinakpani Mandal	2501CS56	2501cs56@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS57	student-ishan	student	Ishan Kumar	2501CS57	2501cs57@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS58	student-kalathiya	student	Kalathiya Priyank Palak	2501CS58	2501cs58@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS59	student-angel	student	Angel Mahi Sharma	2501CS59	2501cs59@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS60	student-kunal	student	Kunal Raj	2501CS60	2501cs60@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS61	student-rahul	student	Rahul Kumar	2501CS61	2501cs61@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS62	student-shivam-kumar	student	Shivam Kumar	2501CS62	2501cs62@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS63	student-neeradi	student	Neeradi Thanmai	2501CS63	2501cs63@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS64	student-ravi	student	Ravi Raj Prasad	2501CS64	2501cs64@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS65	student-mylavarapu	student	Mylavarapu Vivek	2501CS65	2501cs65@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS66	student-nelluri	student	Nelluri Sai Sri Harsha	2501CS66	2501cs66@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS67	student-ishan-srivastava	student	Ishan Srivastava	2501CS67	2501cs67@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS68	student-nihal	student	Nihal Saini	2501CS68	2501cs68@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS69	student-amit	student	Amit Sunil Ahirrao	2501CS69	2501cs69@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS70	student-kimidi	student	Kimidi Pardhiv	2501CS70	2501cs70@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS71	student-vishesh	student	Vishesh Agrawal	2501CS71	2501cs71@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS72	student-parnapalli	student	Parnapalli Avulannagar	2501CS72	2501cs72@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS73	student-shinde	student	Shinde Siddham Subha	2501CS73	2501cs73@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS74	student-aditya-raj	student	Aditya Raj	2501CS74	2501cs74@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS75	student-yenninti	student	Yenninti Laxman	2501CS75	2501cs75@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS76	student-pratyay	student	Pratyay Garg	2501CS76	2501cs76@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS77	student-katravath	student	Katravath Vinod	2501CS77	2501cs77@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS78	student-ishan-alam	student	Ishan Alam	2501CS78	2501cs78@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS79	student-vittal	student	Vittal Das A	2501CS79	2501cs79@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS80	student-mohit	student	Mohit Kumar	2501CS80	2501cs80@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS81	student-shivank	student	Shivank Man	2501CS81	2501cs81@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS82	student-ansh	student	Ansh Motghare	2501CS82	2501cs82@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS83	student-mohit-peswani	student	Mohit Peswani	2501CS83	2501cs83@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS85	student-vikki	student	Vikki Kumar	2501CS85	2501cs85@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS86	student-smruti	student	Smruti Ranjan Sahu	2501CS86	2501cs86@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS87	student-kuldeep	student	Kuldeep Kumar Roy	2501CS87	2501cs87@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS88	student-lutta	student	Lutta Ananya	2501CS88	2501cs88@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS89	student-goutam	student	Goutam Kumar Ghosal	2501CS89	2501cs89@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CS90	student-neha	student	Neha Gupta	2501CS90	2501cs90@example.edu	2026-09-15 21:01:15.329747+00	student	t
2501CS91	student-kabir	student	Kabir Mehta	2501CS91	2501cs91@example.edu	2026-09-15 21:01:15.329747+00	student	t
2501CS92	student-vikram	student	Vikram Singh	2501CS92	2501cs92@example.edu	2026-09-15 21:01:15.329747+00	student	t
2502CS01	student-arnav	student	Arnav Rastogi	2502CS01	2502cs01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS02	student-baibhaw	student	Baibhaw Kumar	2502CS02	2502cs02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS03	student-shubham	student	Shubham	2502CS03	2502cs03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS04	student-kartik	student	Kartik Jitendra Tetwar	2502CS04	2502cs04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS05	student-daksh	student	Daksh Mittal	2502CS05	2502cs05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS06	student-pratyush	student	Pratyush Singh	2502CS06	2502cs06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS07	student-kondala	student	Kondala Rushi Teja	2502CS07	2502cs07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS08	student-mahak	student	Mahak Banyala	2502CS08	2502cs08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2502CS09	student-mohd	student	Mohd Shuaib	2502CS09	2502cs09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CB01	student-adarsh	student	Adarsh Choudhary	2503CB01	2503cb01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CB02	student-amoolya	student	Amoolya Sharan	2503CB02	2503cb02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CB03	student-tejveer	student	Tejveer	2503CB03	2503cb03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CB04	student-yash-madhok	student	Yash Madhok	2503CB04	2503cb04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CB05	student-dheeraj	student	Dheeraj Kumar	2503CB05	2503cb05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CS01	student-sourav	student	Sourav Bhakat	2503CS01	2503cs01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CS02	student-meer	student	Meer Riteshkumar Kapadia	2503CS02	2503cs02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CS03	student-digvijay	student	Digvijay Suresh Zarekar	2503CS03	2503cs03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CS04	student-aniska	student	Aniska Saha	2503CS04	2503cs04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2503CS05	student-guguloth-kumar	student	Guguloth Venu Kumar	2503CS05	2503cs05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI01	student-nukala	student	NUKALA VENKATA CHANDRAHAS	2601AI01	2601ai01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI02	student-annamanani	student	ANNAMANANI ASHWADH	2601AI02	2601ai02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI03	student-yeruva	student	YERUVA PRAHARSHINI	2601AI03	2601ai03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI04	student-kanak	student	Kanak Agrawal	2601AI04	2601ai04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI05	student-bhavya	student	Bhavya Rathi	2601AI05	2601ai05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI06	student-jatothu	student	JATOTHU SAI CHAITANYA	2601AI06	2601ai06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI07	student-aryan-gautam	student	Aryan Gautam	2601AI07	2601ai07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI08	student-aditya-parmar	student	ADITYA PARMAR	2601AI08	2601ai08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI09	student-priyanshu	student	Priyanshu	2601AI09	2601ai09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI10	student-radhika	student	Radhika	2601AI10	2601ai10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI11	student-aanya	student	Aanya Choudhary	2601AI11	2601ai11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI12	student-mayank	student	Mayank Sharma	2601AI12	2601ai12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI13	student-mereddy	student	Mereddy Neha Reddy	2601AI13	2601ai13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI14	student-harshit	student	Harshit Kumar	2601AI14	2601ai14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI15	student-mulkala	student	MULKALA VASHISTA	2601AI15	2601ai15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI16	student-aditi	student	ADITI VERMA	2601AI16	2601ai16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI17	student-gudala	student	GUDALA YOZAN BABU	2601AI17	2601ai17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI18	student-saujanya	student	Saujanya Singh	2601AI18	2601ai18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI19	student-potnuru	student	POTNURU MURALI SRI KRISHNA	2601AI19	2601ai19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI20	student-yash-2	student	Yash	2601AI20	2601ai20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI21	student-gundu	student	GUNDU HARDIK	2601AI21	2601ai21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI22	student-modadugu	student	MODADUGU VENKATA SAI SIVA	2601AI22	2601ai22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI23	student-abhikshit	student	Abhikshit Singh	2601AI23	2601ai23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI24	student-viraj	student	Viraj Singh	2601AI24	2601ai24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI25	student-aditya-thakur	student	ADITYA THAKUR	2601AI25	2601ai25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI26	student-samyaraj	student	Samyaraj Pal	2601AI26	2601ai26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI27	student-omdeep	student	OMDEEP SARKAR	2601AI27	2601ai27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI28	student-patel	student	PATEL LOKESH	2601AI28	2601ai28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI29	student-rahane	student	Rahane Anish Sanjay	2601AI29	2601ai29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI30	student-vanapalli	student	VANAPALLI YASASWINI	2601AI30	2601ai30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI31	student-mamidi	student	MAMIDI VISHNU VARDHAN	2601AI31	2601ai31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI32	student-kandibanda	student	Kandibanda Nehal	2601AI32	2601ai32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI33	student-lakavath	student	LAKAVATH SANTHOSH	2601AI33	2601ai33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI34	student-kuldeep-vaghamshi	student	Kuldeep Vaghamshi	2601AI34	2601ai34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI35	student-anubhav	student	ANUBHAV HIMATSINGKA	2601AI35	2601ai35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI36	student-sachin-prakash	student	Sachin Prakash	2601AI36	2601ai36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI37	student-voni	student	Voni srivalli	2601AI37	2601ai37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI38	student-amara	student	AMARA DURGA VENKATA DHEERAJ	2601AI38	2601ai38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI39	student-kratarth	student	Kratarth Shrivastava	2601AI39	2601ai39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI40	student-kesugani	student	Kesugani Pranay Dev Maharaj	2601AI40	2601ai40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI41	student-gumpu	student	GUMPU PUNEETH SASANK	2601AI41	2601ai41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI42	student-kollu	student	Kollu Venkata Abhinash	2601AI42	2601ai42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI43	student-parlapalli	student	PARLAPALLI SURYA SRIKAR REDDY	2601AI43	2601ai43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI44	student-tokalwad	student	Tokalwad Parth Anand	2601AI44	2601ai44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI45	student-anushka-gupta	student	ANUSHKA GUPTA	2601AI45	2601ai45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI46	student-palakonda	student	PALAKONDA RITVIKREDDY	2601AI46	2601ai46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI47	student-ashish	student	ASHISH KUMAR	2601AI47	2601ai47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI48	student-kada	student	Kada Darshan	2601AI48	2601ai48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI49	student-yepparika	student	YEPPARIKA TEJASWANTH	2601AI49	2601ai49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI50	student-sarthak-kumar	student	Sarthak Kumar	2601AI50	2601ai50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601AI51	student-gargi	student	Gargi	2601AI51	2601ai51@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB01	student-shorya-sharma	student	SHORYA SHARMA	2601CB01	2601cb01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB02	student-aditi-kumari	student	Aditi Kumari	2601CB02	2601cb02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB03	student-animesh	student	Animesh Kumar Jha	2601CB03	2601cb03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB04	student-rathod	student	Rathod Rithesh	2601CB04	2601cb04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB05	student-siriki	student	Siriki Hemanth	2601CB05	2601cb05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB06	student-anshul	student	Anshul Tyagi	2601CB06	2601cb06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB07	student-kota	student	KOTA MANIDEEP	2601CB07	2601cb07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB08	student-adarsh-mohanty	student	Adarsh Mohanty	2601CB08	2601cb08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB09	student-manash	student	MANASH KACHARI	2601CB09	2601cb09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB10	student-krishna	student	KRISHNA SARDAR	2601CB10	2601cb10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB11	student-jeetesh	student	Jeetesh kumar sahu	2601CB11	2601cb11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB12	student-utkarsh	student	UTKARSH YADAV	2601CB12	2601cb12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB13	student-ishan-saraswat	student	Ishan Saraswat	2601CB13	2601cb13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB14	student-tej	student	Tej Pratap	2601CB14	2601cb14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB15	student-dipesh	student	Dipesh Prajapat	2601CB15	2601cb15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB16	student-shreyas	student	Shreyas Gaurav Tarway	2601CB16	2601cb16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB17	student-shourya	student	Shourya Pandey	2601CB17	2601cb17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB18	student-ishita	student	Ishita Singh	2601CB18	2601cb18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB19	student-abhinaba	student	ABHINABA GHOSH	2601CB19	2601cb19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB20	student-agniva	student	Agniva Biswas	2601CB20	2601cb20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB21	student-jharana	student	Jharana Lathigara	2601CB21	2601cb21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB22	student-adway	student	Adway Vijay Shinde	2601CB22	2601cb22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB23	student-ujwal	student	UJWAL KUMAR JHA	2601CB23	2601cb23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB24	student-ayush-gupta	student	Ayush Gupta	2601CB24	2601cb24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB25	student-tanushka	student	Tanushka Sharma	2601CB25	2601cb25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB26	student-swarit	student	Swarit Srivastava	2601CB26	2601cb26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB27	student-sameer	student	Sameer Kardam	2601CB27	2601cb27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB28	student-yadlapalli	student	Yadlapalli Sahiti	2601CB28	2601cb28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB29	student-gaurav-agnihotri	student	Gaurav Agnihotri	2601CB29	2601cb29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB30	student-mohammad	student	MOHAMMAD IBRAHIM	2601CB30	2601cb30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB31	student-samarth	student	Samarth Pratap Singh	2601CB31	2601cb31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB32	student-satyam	student	SATYAM KUMAR KASHYAP	2601CB32	2601cb32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB33	student-ranveer	student	Ranveer Raj	2601CB33	2601cb33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB34	student-yogeshwar	student	Yogeshwar Singh	2601CB34	2601cb34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB35	student-abhay	student	Abhay Yadav	2601CB35	2601cb35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB36	student-nikhil	student	Nikhil Sonkar	2601CB36	2601cb36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB37	student-omraj	student	OMRAJ KUMAR	2601CB37	2601cb37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB38	student-khushi	student	Khushi Kishor Paulbudhe	2601CB38	2601cb38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB39	student-satyam-kumar	student	Satyam Kumar	2601CB39	2601cb39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB40	student-tanay	student	Tanay Sanghvi	2601CB40	2601cb40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB41	student-wathore	student	WATHORE HARSH DATTA	2601CB41	2601cb41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB42	student-abhinav-singh	student	ABHINAV SINGH	2601CB42	2601cb42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB43	student-ayush-raj	student	Ayush Raj	2601CB43	2601cb43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB44	student-soham	student	Soham Ghosh	2601CB44	2601cb44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB45	student-aditya-gupta	student	Aditya Gupta	2601CB45	2601cb45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB46	student-shobhit	student	Shobhit airan	2601CB46	2601cb46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB47	student-nasir	student	Nasir Raza	2601CB47	2601cb47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB48	student-jitin	student	JITIN KUMAR	2601CB48	2601cb48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB49	student-shubhi	student	Shubhi Jain	2601CB49	2601cb49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB50	student-pushpraj	student	Pushpraj Nigwal	2601CB50	2601cb50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB51	student-akula	student	AKULA ANJANA SOWMYA	2601CB51	2601cb51@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB52	student-shagun	student	Shagun Singh	2601CB52	2601cb52@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB53	student-nikhil-2	student	NIKHIL	2601CB53	2601cb53@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB54	student-pintu	student	Pintu Mondal	2601CB54	2601cb54@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB55	student-varahi	student	Varahi Rohit Pardeshi	2601CB55	2601cb55@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB56	student-mudavath	student	MUDAVATH DIVYA	2601CB56	2601cb56@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB57	student-sharad	student	Sharad Rajesh Namdeo	2601CB57	2601cb57@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB58	student-umesh	student	Umesh Soni	2601CB58	2601cb58@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB59	student-illa	student	ILLA RAMYA	2601CB59	2601cb59@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB60	student-lohit	student	lohit s	2601CB60	2601cb60@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB61	student-ankit	student	Ankit Kumar Subai	2601CB61	2601cb61@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB62	student-sampathi	student	SAMPATHI MAYANK	2601CB62	2601cb62@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB63	student-gyanvi	student	Gyanvi Priya	2601CB63	2601cb63@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB64	student-peddaram	student	Peddaram Sahasra Vardhini	2601CB64	2601cb64@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB65	student-gangapatnam	student	gangapatnam shyam abhishek	2601CB65	2601cb65@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB66	student-guguloth-shekar	student	GUGULOTH SHEKAR	2601CB66	2601cb66@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CB67	student-kevlani	student	Kevlani Yash Manishbhai	2601CB67	2601cb67@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE01	student-om	student	Om Parth	2601CE01	2601ce01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE02	student-mahi	student	Mahi Agrawal	2601CE02	2601ce02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE03	student-nishant	student	Nishant Singh	2601CE03	2601ce03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE04	student-kurva	student	KURVA ABHISHEK	2601CE04	2601ce04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE05	student-vipin	student	VIPIN KUMAR	2601CE05	2601ce05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE06	student-priyamgaurvi	student	Priyamgaurvi	2601CE06	2601ce06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE07	student-pratham	student	Pratham Singla	2601CE07	2601ce07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE08	student-animesh-shukla	student	Animesh Shukla	2601CE08	2601ce08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE09	student-kishan	student	KISHAN KUMAR	2601CE09	2601ce09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE10	student-anupam-jha	student	Anupam Jha	2601CE10	2601ce10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE11	student-harsh	student	HARSH PRATAP SINGH	2601CE11	2601ce11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE12	student-aarju	student	Aarju	2601CE12	2601ce12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE13	student-chetan	student	Chetan Singh	2601CE13	2601ce13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE14	student-anand	student	Anand Kumar	2601CE14	2601ce14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE15	student-snigdh	student	Snigdh Arindam	2601CE15	2601ce15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE16	student-arpit	student	ARPIT MISHRA	2601CE16	2601ce16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE17	student-vivek	student	VIVEK GOYAL	2601CE17	2601ce17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE18	student-arya	student	Arya Deshmukh	2601CE18	2601ce18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE19	student-gajendra	student	GAJENDRA KUMAR JAT	2601CE19	2601ce19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE20	student-rahul-nagora	student	Rahul Nagora	2601CE20	2601ce20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE21	student-harsh-saini	student	Harsh Saini	2601CE21	2601ce21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE22	student-dharamveer	student	Dharamveer pingoliya	2601CE22	2601ce22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE23	student-dasu	student	Dasu Jayasree	2601CE23	2601ce23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE24	student-saumya	student	SAUMYA SHARMA	2601CE24	2601ce24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE25	student-rishabh	student	RISHABH SINGH	2601CE25	2601ce25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE26	student-ameya	student	AMEYA PRAVIN KAMAT	2601CE26	2601ce26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603AI05	student-mohit-kumar	student	Mohit kumar	2603AI05	2603ai05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE27	student-sarthak-samanta	student	SARTHAK KUMAR DHIR SAMANTA	2601CE27	2601ce27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE28	student-tammireddi	student	TAMMIREDDI PRANATHI	2601CE28	2601ce28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE29	student-prashant-meena	student	Prashant meena	2601CE29	2601ce29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE30	student-rakesh	student	Rakesh Jangid	2601CE30	2601ce30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE31	student-vivek-meena	student	Vivek meena	2601CE31	2601ce31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE32	student-sudhanshu	student	SUDHANSHU SANJAY AJGAONKAR	2601CE32	2601ce32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE33	student-atul	student	ATUL BARWAL	2601CE33	2601ce33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE34	student-sabavat	student	SABAVAT AISHWARYA	2601CE34	2601ce34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE35	student-vaibhav-anand	student	VAIBHAV ANAND	2601CE35	2601ce35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE36	student-sarvjeet	student	Sarvjeet Kumar	2601CE36	2601ce36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE37	student-aanya-verma	student	aanya verma	2601CE37	2601ce37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE38	student-aryan-rai	student	Aryan Rai	2601CE38	2601ce38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE39	student-wriddhi	student	Wriddhi Adhya	2601CE39	2601ce39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE40	student-pritam	student	Pritam Kumar Siddhant	2601CE40	2601ce40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE41	student-balajii	student	Balajii Jha	2601CE41	2601ce41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE42	student-aditya-singh	student	Aditya Singh	2601CE42	2601ce42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE43	student-mohammad-kamran	student	MOHAMMAD KAMRAN	2601CE43	2601ce43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE44	student-shivam-raj	student	SHIVAM RAJ	2601CE44	2601ce44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE45	student-pradip	student	PRADIP KUMAR	2601CE45	2601ce45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE46	student-harsh-sharma	student	Harsh Sharma	2601CE46	2601ce46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE47	student-shreya-kumari	student	Shreya Kumari	2601CE47	2601ce47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE48	student-gurram	student	GURRAM AKSHARA	2601CE48	2601ce48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE49	student-vaibhav-pankaj	student	Vaibhav Pankaj	2601CE49	2601ce49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE50	student-shaik	student	Shaik Arbaaz Ahmed	2601CE50	2601ce50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE51	student-ahon	student	Ahon Pansa	2601CE51	2601ce51@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE52	student-vankudoth	student	VANKUDOTH RAMCHARAN	2601CE52	2601ce52@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE53	student-harshit-mangal	student	Harshit Mangal	2601CE53	2601ce53@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE54	student-mahi-khera	student	Mahi Khera	2601CE54	2601ce54@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE55	student-deepak	student	Deepak Singh	2601CE55	2601ce55@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE56	student-lokesh	student	Lokesh yadav	2601CE56	2601ce56@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE57	student-abhijeet	student	Abhijeet Kumar	2601CE57	2601ce57@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE58	student-anurag	student	Anurag Jha	2601CE58	2601ce58@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE59	student-jatin	student	Jatin	2601CE59	2601ce59@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE60	student-gaurav-kumar	student	GAURAV KUMAR	2601CE60	2601ce60@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE61	student-yogendra	student	YOGENDRA KUMAR RAWAT	2601CE61	2601ce61@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE62	student-aman-kumar	student	Aman Kumar	2601CE62	2601ce62@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE63	student-rohit	student	Rohit dulariya	2601CE63	2601ce63@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CE64	student-tholisaku	student	Tholisaku sruthi	2601CE64	2601ce64@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS01	student-vadthyavath	student	VADTHYAVATH BHUVANENDRA NAIK	2601CS01	2601cs01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS02	student-gajendra-sarathe	student	Gajendra Sarathe	2601CS02	2601cs02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS03	student-daksh-joshi	student	Daksh Joshi	2601CS03	2601cs03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS04	student-aryan-raj	student	Aryan Raj	2601CS04	2601cs04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS05	student-jakkampudi	student	Jakkampudi Tanuj	2601CS05	2601cs05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS06	student-aditya-negi	student	Aditya Negi	2601CS06	2601cs06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS07	student-khushi-agrawal	student	Khushi Agrawal	2601CS07	2601cs07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS08	student-shubhkarmandeep	student	Shubhkarmandeep Singh	2601CS08	2601cs08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS09	student-parminder	student	Parminder Mittal	2601CS09	2601cs09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS10	student-vankunavath	student	Vankunavath Shashank Indra tej	2601CS10	2601cs10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS11	student-yogyta	student	YOGYTA VERMA	2601CS11	2601cs11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS12	student-mohammad-husain	student	Mohammad Husain	2601CS12	2601cs12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS13	student-varanasi	student	varanasi abhiram	2601CS13	2601cs13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS14	student-shivam-sahoo	student	SHIVAM SAHOO	2601CS14	2601cs14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS15	student-narottam	student	Narottam Singh Sikarwar	2601CS15	2601cs15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS16	student-biswajit	student	Biswajit Sahoo	2601CS16	2601cs16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS17	student-gotam	student	Gotam	2601CS17	2601cs17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS18	student-vekariya	student	Vekariya Smit Naranbhai	2601CS18	2601cs18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS19	student-gajibelli	student	GAJIBELLI PUSHPA VAMSI	2601CS19	2601cs19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS20	student-garv	student	Garv Singh Gaharwar	2601CS20	2601cs20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS21	student-ankit-mishra	student	ANKIT MISHRA	2601CS21	2601cs21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS22	student-kalluru	student	KALLURU DEEKSHITHA REDDY	2601CS22	2601cs22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS23	student-shristy	student	Shristy Kumari	2601CS23	2601cs23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS24	student-jadhav	student	JADHAV PRAJYOT	2601CS24	2601cs24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS25	student-bhujuti	student	BHUJUTI BILVIKA	2601CS25	2601cs25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS26	student-pratik	student	Pratik Rajabapu Kesbhat	2601CS26	2601cs26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS27	student-talasani	student	Talasani Rithwik Reddy	2601CS27	2601cs27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS28	student-jeswanth	student	JESWANTH C S	2601CS28	2601cs28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS29	student-patibandla	student	PATIBANDLA AKASH	2601CS29	2601cs29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS30	student-mudokulam	student	MUDOKULAM JAIKISHAN NAIK	2601CS30	2601cs30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS31	student-utkarsh-raj	student	Utkarsh Raj	2601CS31	2601cs31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS32	student-k	student	K Rahul Kumar reddy	2601CS32	2601cs32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS33	student-aditya-singh-2	student	Aditya Singh	2601CS33	2601cs33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS34	student-kuluri	student	kuluri venkata sai kaushik	2601CS34	2601cs34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS35	student-neralwar	student	NERALWAR CHAANAKYA DAAMAN	2601CS35	2601cs35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS36	student-avinash	student	Avinash Shakya	2601CS36	2601cs36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS37	student-grisha	student	Grisha Garg	2601CS37	2601cs37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS38	student-rishabh-rai	student	Rishabh Rai	2601CS38	2601cs38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS39	student-kurupudi	student	kurupudi sai sathvika	2601CS39	2601cs39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS40	student-raghav	student	RAGHAV JESANI	2601CS40	2601cs40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS41	student-v	student	V VARUNKUMAR	2601CS41	2601cs41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS42	student-krishna-kumar	student	Krishna Kumar	2601CS42	2601cs42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS43	student-dhruv-2	student	Dhruv	2601CS43	2601cs43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS44	student-poura	student	Poura Venkata Bhavesh	2601CS44	2601cs44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS45	student-aditya-kashyap	student	Aditya Kashyap	2601CS45	2601cs45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS46	student-darshana	student	Darshana Rawatale	2601CS46	2601cs46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS47	student-pramod	student	PRAMOD YADAV	2601CS47	2601cs47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS48	student-karan	student	Karan Rajput	2601CS48	2601cs48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS49	student-lapshetwar	student	LAPSHETWAR SHIVAM PRADIP	2601CS49	2601cs49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS50	student-abhishek-kumar	student	Abhishek Kumar	2601CS50	2601cs50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS51	student-kottisa	student	KOTTISA NIKHITH	2601CS51	2601cs51@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS52	student-shivansh	student	Shivansh Tripathi	2601CS52	2601cs52@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS53	student-ayushman	student	Ayushman Ghatak	2601CS53	2601cs53@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS54	student-harsh-patel	student	harsh patel	2601CS54	2601cs54@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS55	student-kethireddy	student	kethireddy Nagapuneeth Reddy	2601CS55	2601cs55@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS56	student-suhani	student	Suhani Gulati	2601CS56	2601cs56@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS57	student-vemu	student	Vemu Manjula	2601CS57	2601cs57@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS58	student-aamana	student	AAMANA KHATOON	2601CS58	2601cs58@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS59	student-katrodiya	student	KATRODIYA PRINCE BIPIN	2601CS59	2601cs59@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS60	student-yashas	student	Yashas Prasanna	2601CS60	2601cs60@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS61	student-dhondre	student	Dhondre Soniya Ganesh	2601CS61	2601cs61@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS62	student-utkarsha	student	UTKARSHA RAVINDRA KAKULATE	2601CS62	2601cs62@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS63	student-navneet	student	NAVNEET KUMAR NITIN	2601CS63	2601cs63@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS64	student-noor	student	Noor Jamali	2601CS64	2601cs64@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS65	student-yellapu	student	Yellapu Akhila	2601CS65	2601cs65@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS66	student-perumalla	student	PERUMALLA ABHIJITH	2601CS66	2601cs66@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS67	student-ambati	student	AMBATI KEERTHI PRANAVI	2601CS67	2601cs67@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS68	student-debrup	student	Debrup Roy	2601CS68	2601cs68@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS69	student-srivally	student	SRIVALLY PERUMANDLA	2601CS69	2601cs69@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS70	student-anmol	student	Anmol Kumar Sah	2601CS70	2601cs70@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS71	student-dakarapu	student	DAKARAPU SAIJEETH	2601CS71	2601cs71@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS72	student-atishay	student	Atishay Jain	2601CS72	2601cs72@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS73	student-nihal-shoju	student	Nihal Shoju	2601CS73	2601cs73@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS74	student-utkarsh-raj-2	student	Utkarsh Raj	2601CS74	2601cs74@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS75	student-aman-kumar-2	student	Aman Kumar	2601CS75	2601cs75@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS76	student-devesh	student	Devesh Kumar	2601CS76	2601cs76@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS77	student-prerak	student	Prerak	2601CS77	2601cs77@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS78	student-shrishant	student	SHRISHANT KUMAR	2601CS78	2601cs78@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS79	student-tirth	student	Tirth Sorthiya	2601CS79	2601cs79@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS80	student-indukuri	student	Indukuri Kishore Reddy	2601CS80	2601cs80@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS81	student-mukiri	student	Mukiri Saatwik	2601CS81	2601cs81@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS82	student-umesh-saini	student	UMESH KUMAR SAINI	2601CS82	2601cs82@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS83	student-ashish-kumar	student	Ashish Kumar	2601CS83	2601cs83@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS84	student-krish	student	Krish	2601CS84	2601cs84@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS85	student-chaitanaya	student	Chaitanaya Nathalia	2601CS85	2601cs85@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS86	student-kanad	student	Kanad Laxman Kumavat	2601CS86	2601cs86@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS87	student-vaibhav-2	student	Vaibhav	2601CS87	2601cs87@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CS88	student-ramavath	student	Ramavath Vinay	2601CS88	2601cs88@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT01	student-shaurya	student	Shaurya Gupta	2601CT01	2601ct01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT02	student-arpit-raut	student	Arpit Ravikiran Raut	2601CT02	2601ct02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT03	student-akshit	student	AKSHIT SHARMA	2601CT03	2601ct03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT04	student-prince	student	Prince	2601CT04	2601ct04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT05	student-aarya	student	Aarya Pankaj Patil	2601CT05	2601ct05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT06	student-mandhani	student	Mandhani Netal Radheshyam	2601CT06	2601ct06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT07	student-raj-gupta	student	Raj Gupta	2601CT07	2601ct07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT08	student-amey	student	Amey Mittal	2601CT08	2601ct08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT09	student-nitya	student	Nitya Bansal	2601CT09	2601ct09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT10	student-manya	student	Manya Dhirawat	2601CT10	2601ct10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT11	student-ananya-kumari	student	Ananya Kumari	2601CT11	2601ct11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT12	student-prince-choudhary	student	Prince Choudhary	2601CT12	2601ct12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT13	student-mane	student	MANE KANISHK RAJARAM	2601CT13	2601ct13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT14	student-kashvi	student	Kashvi Verma	2601CT14	2601ct14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT15	student-riyansh	student	Riyansh	2601CT15	2601ct15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT16	student-archit-tulsyan	student	ARCHIT TULSYAN	2601CT16	2601ct16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT17	student-mayank-jangid	student	Mayank Jangid	2601CT17	2601ct17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT18	student-s-kavisan	student	S Kavisan	2601CT18	2601ct18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT19	student-brijesh	student	Brijesh Nishad	2601CT19	2601ct19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT20	student-rahul-singh	student	RAHUL SINGH	2601CT20	2601ct20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT21	student-ritesh-kumar	student	Ritesh kumar	2601CT21	2601ct21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT22	student-karan-kumar	student	Karan kumar	2601CT22	2601ct22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT23	student-arnav-agrawal	student	Arnav Agrawal	2601CT23	2601ct23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT24	student-devansh	student	Devansh Bansal	2601CT24	2601ct24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT25	student-aman-kumar-3	student	Aman Kumar	2601CT25	2601ct25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT26	student-harshit-sharma	student	HARSHIT CHANDRA SHARMA	2601CT26	2601ct26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT27	student-peddabomma	student	Peddabomma Hari Hara Teja	2601CT27	2601ct27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT28	student-madhav	student	madhav sharma	2601CT28	2601ct28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT29	student-yukta	student	Yukta Singh	2601CT29	2601ct29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT30	student-ashu	student	ASHU ANAND	2601CT30	2601ct30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT31	student-dharavath	student	DHARAVATH DEEPANVITHA	2601CT31	2601ct31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT32	student-tanav	student	Tanav	2601CT32	2601ct32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT33	student-korra	student	Korra Arun	2601CT33	2601ct33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT34	student-himesh	student	HIMESH GHOSLIYA	2601CT34	2601ct34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT35	student-siddatapu	student	Siddatapu Ajay kumar	2601CT35	2601ct35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601CT36	student-arnav-thakare	student	Arnav Thakare	2601CT36	2601ct36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC01	student-fatima	student	Fatima Bint Kashif	2601EC01	2601ec01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC02	student-girivardhan	student	Girivardhan A R	2601EC02	2601ec02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC03	student-asif	student	Asif Uddaulah	2601EC03	2601ec03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC04	student-srirup	student	Srirup Saha	2601EC04	2601ec04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC05	student-mane-krishna	student	MANE SAI KRISHNA	2601EC05	2601ec05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC06	student-shlok	student	Shlok Kumar	2601EC06	2601ec06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC07	student-bondugula	student	BONDUGULA LIKITH SAI	2601EC07	2601ec07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC08	student-lingam	student	Lingam Rohit	2601EC08	2601ec08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC09	student-amula	student	AMULA SAHITHI	2601EC09	2601ec09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC10	student-dev	student	Dev Pathak	2601EC10	2601ec10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC11	student-harshit-singh	student	HARSHIT SINGH	2601EC11	2601ec11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC12	student-valluri	student	VALLURI JEEVANAHARIKA	2601EC12	2601ec12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC13	student-prince-sharma	student	Prince Sharma	2601EC13	2601ec13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC14	student-garima	student	Garima	2601EC14	2601ec14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC15	student-allu	student	ALLU SAI JAGAN	2601EC15	2601ec15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC16	student-kashyap	student	KASHYAP CHANDRASHEKHAR BAGDE	2601EC16	2601ec16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC17	student-natte	student	Natte Charan Sai Teja	2601EC17	2601ec17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC18	student-kartikeya	student	Kartikeya Kumar Srivastava	2601EC18	2601ec18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC19	student-vedansh	student	Vedansh Tandon	2601EC19	2601ec19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC20	student-deepanshu	student	Deepanshu Jangir	2601EC20	2601ec20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC21	student-pedada	student	PEDADA YUVA SAMAIKYA	2601EC21	2601ec21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC22	student-aman-anand	student	Aman Anand	2601EC22	2601ec22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC23	student-swarali	student	Swarali Sarang Bhola	2601EC23	2601ec23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC24	student-jaybir	student	Jaybir Swami	2601EC24	2601ec24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC25	student-shaik-akthar	student	shaik sohel akthar	2601EC25	2601ec25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC26	student-yuvraj	student	Yuvraj Singh	2601EC26	2601ec26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC27	student-srinaina	student	Srinaina Gowru	2601EC27	2601ec27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC28	student-threenender	student	THREENENDER BHUKYA	2601EC28	2601ec28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC29	student-anirudh	student	Anirudh G	2601EC29	2601ec29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC30	student-damor	student	Damor Prant Narendrasinh	2601EC30	2601ec30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC31	student-mallika	student	MALLIKA LOKESH	2601EC31	2601ec31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC32	student-panthangi	student	Panthangi Abhishek	2601EC32	2601ec32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC33	student-ramhungneile	student	Ramhungneile Nriame	2601EC33	2601ec33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC34	student-mardala	student	MARDALA YOGI PRATHAP	2601EC34	2601ec34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC35	student-taneti	student	TANETI VENKATA RAMA KANTH	2601EC35	2601ec35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC36	student-suyash	student	SUYASH SRIVASTAVA	2601EC36	2601ec36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC37	student-abhivadan	student	Abhivadan Srivastava	2601EC37	2601ec37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC38	student-piyush	student	PIYUSH KUMAR	2601EC38	2601ec38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC39	student-shubh	student	Shubh Laxmi	2601EC39	2601ec39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC40	student-buyyala	student	Buyyala Rishitha	2601EC40	2601ec40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC41	student-suyash-verma	student	Suyash Verma	2601EC41	2601ec41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC42	student-gavva	student	Gavva Abhiram Reddy	2601EC42	2601ec42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC43	student-krishna-sharma	student	Krishna Sharma	2601EC43	2601ec43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC44	student-shivansh-kumar	student	Shivansh Kumar	2601EC44	2601ec44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC45	student-shah	student	SHAH VRAJ KETUL	2601EC45	2601ec45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EC46	student-komal	student	KOMAL KUMARI	2601EC46	2601ec46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE01	student-satya	student	Satya Kumar Shubham	2601EE01	2601ee01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE02	student-mehul	student	MEHUL KUMAR	2601EE02	2601ee02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE03	student-mankhush	student	Mankhush	2601EE03	2601ee03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE04	student-bhagat	student	Bhagat Anushka Satyaprakash	2601EE04	2601ee04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE05	student-purnim	student	Purnim Raj	2601EE05	2601ee05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE06	student-shreyansh	student	Shreyansh Agarwal	2601EE06	2601ee06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE07	student-ayush-narayan	student	Ayush Narayan	2601EE07	2601ee07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE08	student-ayush-raj-2	student	Ayush Raj	2601EE08	2601ee08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE09	student-pratyush-sharma	student	PRATYUSH SHARMA	2601EE09	2601ee09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE10	student-brajendra	student	Brajendra Kumar	2601EE10	2601ee10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE11	student-shashank	student	Shashank Vardhan	2601EE11	2601ee11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE12	student-mukund	student	Mukund Madhav B	2601EE12	2601ee12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE13	student-prajeeth	student	Prajeeth Batchu	2601EE13	2601ee13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE14	student-rudra	student	Rudra Pratap Prajapat	2601EE14	2601ee14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE15	student-sumit	student	Sumit Sarkar	2601EE15	2601ee15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE16	student-alok	student	Alok Raj	2601EE16	2601ee16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE17	student-sreeman	student	SREEMAN BURAM	2601EE17	2601ee17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE18	student-subham	student	SUBHAM GHOSH	2601EE18	2601ee18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE19	student-mandadi	student	MANDADI SIRIJA	2601EE19	2601ee19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE20	student-anushree	student	Anushree Gupta	2601EE20	2601ee20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE21	student-naitik	student	Naitik Gupta	2601EE21	2601ee21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE22	student-raj-shekhar	student	Raj Shekhar	2601EE22	2601ee22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE23	student-pratyusha	student	Pratyusha Maji	2601EE23	2601ee23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE24	student-ambala	student	AMBALA ATHRIJ	2601EE24	2601ee24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE25	student-gugulothu	student	Gugulothu Ram charan	2601EE25	2601ee25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE26	student-samir	student	Samir Kumar	2601EE26	2601ee26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE27	student-abhigyan	student	Abhigyan Singh	2601EE27	2601ee27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE28	student-abhayanand	student	Abhayanand Kumar	2601EE28	2601ee28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE29	student-ranveer-singh	student	Ranveer Singh	2601EE29	2601ee29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE30	student-boda	student	BODA RAM CHARAN	2601EE30	2601ee30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE31	student-harsh-sisodiya	student	Harsh Singh Sisodiya	2601EE31	2601ee31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE32	student-paridhi	student	Paridhi Agrawal	2601EE32	2601ee32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE33	student-ryan	student	Ryan Mathew	2601EE33	2601ee33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE34	student-nandani	student	NANDANI GUPTA	2601EE34	2601ee34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE35	student-ritisha	student	Ritisha Dutta	2601EE35	2601ee35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE36	student-kokkalla	student	KOKKALLA SAI PAVAN TEJ	2601EE36	2601ee36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE37	student-kodavath	student	KODAVATH HARSHAVARDHAN	2601EE37	2601ee37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE38	student-jamalapurapu	student	JAMALAPURAPU SREE SAI DHARAHAAS	2601EE38	2601ee38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE39	student-amit-kumar	student	AMIT KUMAR	2601EE39	2601ee39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE40	student-bhosale	student	BHOSALE SAKSHAM SANJAYKUMAR	2601EE40	2601ee40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE41	student-atul-rai	student	Atul Rai	2601EE41	2601ee41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE42	student-kale	student	KALE SNEHA ZELAJI	2601EE42	2601ee42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE43	student-keerthan	student	Keerthan B T	2601EE43	2601ee43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE44	student-lakavath-anirvinya	student	Lakavath Anirvinya	2601EE44	2601ee44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE45	student-prokash	student	Prokash Mondal	2601EE45	2601ee45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601EE46	student-shaik-nousheer	student	SHAIK NOUSHEER	2601EE46	2601ee46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES01	student-ashutosh	student	Ashutosh anand Shivjee Singh	2601ES01	2601es01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES02	student-rahul-shukla	student	Rahul Shukla	2601ES02	2601es02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES03	student-ashish-raj	student	Ashish Raj	2601ES03	2601es03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES04	student-parth-jaiswal	student	PARTH VIVEK JAISWAL	2601ES04	2601es04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES05	student-maloth	student	Maloth Parimala	2601ES05	2601es05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES06	student-gowtham	student	GOWTHAM A N	2601ES06	2601es06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES07	student-pranava	student	PRANAVA PRADHAN	2601ES07	2601es07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES08	student-rakshita	student	RAKSHITA JANU	2601ES08	2601es08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES09	student-arnav-wakode	student	Arnav Vijay Wakode	2601ES09	2601es09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES10	student-somnath	student	Somnath Majhi	2601ES10	2601es10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES11	student-yajat	student	Yajat Guliyani	2601ES11	2601es11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES12	student-mukul	student	Mukul Athwal	2601ES12	2601es12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES13	student-atharva	student	Atharva Manoj Deshmukh	2601ES13	2601es13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES14	student-didde	student	Didde Ramya	2601ES14	2601es14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES15	student-aman-thakur	student	Aman Kumar Thakur	2601ES15	2601es15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES16	student-charvi	student	Charvi Chandrashekhar Marathe	2601ES16	2601es16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES17	student-abhishek-singh	student	ABHISHEK V SINGH	2601ES17	2601es17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES18	student-dev-tiwari	student	Dev Tiwari	2601ES18	2601es18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES19	student-yadnya	student	Yadnya Namit Satam	2601ES19	2601es19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES20	student-jayshri	student	Jayshri Agarwal	2601ES20	2601es20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES21	student-jayansh	student	Jayansh Poonia	2601ES21	2601es21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES22	student-pradyuman	student	PRADYUMAN SINGH SHEKHAWAT	2601ES22	2601es22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ES23	student-dhondi	student	DHONDI JUGGE PRATHEEK	2601ES23	2601es23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC01	student-verushka	student	Verushka Mamodia	2601MC01	2601mc01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC02	student-harish	student	HARISH ATTRI	2601MC02	2601mc02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC03	student-abhijeet-singh	student	ABHIJEET KUMAR SINGH	2601MC03	2601mc03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC04	student-chandrachur	student	chandrachur mondal	2601MC04	2601mc04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC05	student-lakshya	student	LAKSHYA MALKHEDE	2601MC05	2601mc05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC06	student-saksham	student	SAKSHAM MITTAL	2601MC06	2601mc06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC07	student-incharaa	student	Incharaa Shivaprakash	2601MC07	2601mc07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC08	student-parth-sahu	student	PARTH SAHU	2601MC08	2601mc08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC09	student-anubhu	student	Anubhu Das	2601MC09	2601mc09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC10	student-mahesh	student	MAHESH HOTA	2601MC10	2601mc10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC11	student-arkaprabho	student	Arkaprabho Sau	2601MC11	2601mc11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC12	student-rehan	student	REHAN RIAZAHMAD MULLA	2601MC12	2601mc12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC13	student-chirag	student	Chirag kumar	2601MC13	2601mc13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC14	student-shreyasi	student	Shreyasi	2601MC14	2601mc14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC15	student-devangana	student	Devangana Aneesh	2601MC15	2601mc15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC16	student-satvik	student	Satvik Deorah	2601MC16	2601mc16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC17	student-deepak-kumar	student	Deepak Kumar	2601MC17	2601mc17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC18	student-abhishek-meena	student	Abhishek Meena	2601MC18	2601mc18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC19	student-rachit	student	Rachit Shah	2601MC19	2601mc19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC20	student-yash-sawsakade	student	Yash Purushottam Sawsakade	2601MC20	2601mc20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC21	student-prateek	student	Prateek Daga	2601MC21	2601mc21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC22	student-yogita	student	Yogita	2601MC22	2601mc22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC23	student-murapaka	student	MURAPAKA CHANDRA SEKHAR	2601MC23	2601mc23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC24	student-madhavaram	student	MADHAVARAM SAHARSH	2601MC24	2601mc24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC25	student-nallapu	student	Nallapu Tanish	2601MC25	2601mc25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC26	student-gaurav-maurya	student	Gaurav Singh Maurya	2601MC26	2601mc26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC27	student-arshad	student	Arshad Umar Khan	2601MC27	2601mc27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC28	student-tejas	student	Tejas Babhale	2601MC28	2601mc28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC29	student-kumar	student	Kumar Naman	2601MC29	2601mc29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC30	student-prince-saxena	student	Prince Saxena	2601MC30	2601mc30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC31	student-satyam-2	student	SATYAM	2601MC31	2601mc31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC32	student-varun	student	Varun	2601MC32	2601mc32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC33	student-sourabh	student	Sourabh Kumar	2601MC33	2601mc33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC34	student-rehan-ansari	student	Rehan Ansari	2601MC34	2601mc34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC35	student-suragala	student	SURAGALA SATHWIK	2601MC35	2601mc35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC36	student-geetika	student	Geetika Bhagat	2601MC36	2601mc36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC37	student-banoth	student	Banoth Sidharth	2601MC37	2601mc37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC38	student-ishan-mittal	student	ISHAN MITTAL	2601MC38	2601mc38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC39	student-addala	student	Addala Suhani	2601MC39	2601mc39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC40	student-yash-prasad	student	YASH PRASAD	2601MC40	2601mc40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC41	student-aayush-paikaray	student	Aayush Paikaray	2601MC41	2601mc41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC42	student-banavath	student	BANAVATH BHAVITHA	2601MC42	2601mc42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC43	student-nityasha	student	Nityasha Rajput	2601MC43	2601mc43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC44	student-mothukupally	student	Mothukupally Nihal Reddy	2601MC44	2601mc44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC45	student-tadi	student	Tadi Bhargava Siva Durga	2601MC45	2601mc45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC46	student-shivansh-gupta	student	Shivansh Kumar Gupta	2601MC46	2601mc46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC47	student-md	student	Md Taha Hussain	2601MC47	2601mc47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC48	student-ayush-kumar	student	Ayush Kumar	2601MC48	2601mc48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC49	student-lovedev	student	Lovedev	2601MC49	2601mc49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MC50	student-lakshmi	student	Lakshmi Patni	2601MC50	2601mc50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME01	student-donga	student	Donga Pal Sanjaybhai	2601ME01	2601me01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME02	student-kumar-shankar	student	KUMAR SHANKAR	2601ME02	2601me02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME03	student-mayuresh	student	Mayuresh Rajiv Nande	2601ME03	2601me03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME04	student-chinmay	student	Chinmay Aggarwal	2601ME04	2601me04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME05	student-priyanshi-goyal	student	Priyanshi Goyal	2601ME05	2601me05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME06	student-mohammad-ali	student	Mohammad Ali	2601ME06	2601me06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME07	student-aryan-2	student	aryan	2601ME07	2601me07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME08	student-shreyansh-ravi	student	Shreyansh Ravi	2601ME08	2601me08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME09	student-tatikonda	student	Tatikonda Karthik Reddy	2601ME09	2601me09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME10	student-pradyumna	student	Pradyumna Vasant Patil	2601ME10	2601me10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME11	student-satyam-singh	student	Satyam singh	2601ME11	2601me11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME12	student-gulshan	student	Gulshan kumar	2601ME12	2601me12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME13	student-ajay	student	AJAY KUMAR PANDIT	2601ME13	2601me13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME14	student-varanasi-rishin	student	VARANASI SAI RISHIN	2601ME14	2601me14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME15	student-aman-kumar-4	student	Aman Kumar	2601ME15	2601me15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME16	student-adrita	student	ADRITA BEJ	2601ME16	2601me16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME17	student-krishnam	student	Krishnam	2601ME17	2601me17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME18	student-jai	student	JAI JYOTHI SWAROOP	2601ME18	2601me18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME19	student-harshit-kumar-singh	student	HARSHIT KUMAR SINGH	2601ME19	2601me19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME20	student-puneet	student	Puneet Yadav	2601ME20	2601me20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME21	student-anurag-singh	student	Anurag Singh	2601ME21	2601me21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME22	student-gorle	student	GORLE GNANADEEP	2601ME22	2601me22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME23	student-dulapalli	student	DULAPALLI LEELA KRISHNA	2601ME23	2601me23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME24	student-hazare	student	HAZARE SANVI	2601ME24	2601me24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME25	student-maithreya	student	Maithreya Kompella	2601ME25	2601me25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME26	student-antharam	student	ANTHARAM KEERTHI PRIYA	2601ME26	2601me26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME27	student-dhruv-saxena	student	Dhruv Saxena	2601ME27	2601me27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME28	student-megavath	student	MEGAVATH SAINATH	2601ME28	2601me28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME29	student-navanitha	student	Navanitha J	2601ME29	2601me29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME30	student-mahika	student	Mahika Paliwal	2601ME30	2601me30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME31	student-aprajita	student	Aprajita Pandey	2601ME31	2601me31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME32	student-yashaswi	student	YASHASWI SUDHANV BALANAGU	2601ME32	2601me32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME33	student-gautam	student	GAUTAM KUMAR	2601ME33	2601me33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME34	student-singh	student	SINGH ARYAMAN HARENDRA	2601ME34	2601me34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME35	student-ashish-jacob	student	Ashish Jacob	2601ME35	2601me35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME36	student-aditya-maurya	student	Aditya Maurya	2601ME36	2601me36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME37	student-jajimogga	student	Jajimogga Teja	2601ME37	2601me37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME38	student-namala	student	NAMALA YESHWANTH KUMAR	2601ME38	2601me38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME39	student-kanishk	student	Kanishk Choudhary	2601ME39	2601me39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME40	student-aditya-kumar	student	Aditya Kumar	2601ME40	2601me40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME41	student-gedela	student	GEDELA BALA SAI GANESH	2601ME41	2601me41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME42	student-chhatrala	student	Chhatrala Shan Nishant	2601ME42	2601me42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME43	student-swapnil	student	Swapnil Chowdhury	2601ME43	2601me43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME44	student-s-vadavelli	student	S LITHESH CHETAN VADAVELLI	2601ME44	2601me44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME45	student-jai-bhatia	student	Jai Bhatia	2601ME45	2601me45@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME46	student-krish-kumar	student	Krish Kumar	2601ME46	2601me46@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME47	student-ishita-singh	student	ISHITA SINGH	2601ME47	2601me47@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME48	student-dara	student	DARA VINOOTHNA	2601ME48	2601me48@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME49	student-pranshu	student	Pranshu Agrawal	2601ME49	2601me49@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME50	student-yusuf	student	Yusuf Imtiyaz	2601ME50	2601me50@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME51	student-abhishek-k	student	Abhishek C K	2601ME51	2601me51@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME52	student-kottisa-haripreeth	student	Kottisa Haripreeth	2601ME52	2601me52@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME53	student-yelaka	student	YELAKA MIDHUN SAI	2601ME53	2601me53@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME54	student-gun	student	Gun Agrawal	2601ME54	2601me54@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME55	student-ratan	student	Ratan Kumar Yadav	2601ME55	2601me55@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME56	student-muttamsetti	student	Muttamsetti Jayasri Durga	2601ME56	2601me56@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME57	student-anurag-nath	student	Anurag Nath	2601ME57	2601me57@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME58	student-rishabh-kumar	student	Rishabh kumar	2601ME58	2601me58@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME59	student-poornima	student	POORNIMA TIWARI	2601ME59	2601me59@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME60	student-rudra-mahlawat	student	RUDRA MAHLAWAT	2601ME60	2601me60@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME61	student-shreya-kumari-2	student	Shreya Kumari	2601ME61	2601me61@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME62	student-derin	student	Derin Kurian Jose	2601ME62	2601me62@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME63	student-jiya	student	JIYA AGGARWAL	2601ME63	2601me63@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME64	student-anaghmoy	student	Anaghmoy Chatterjee	2601ME64	2601me64@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME65	student-jupudi	student	JUPUDI GOWTHAM	2601ME65	2601me65@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME66	student-aadya	student	Aadya Singh	2601ME66	2601me66@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME67	student-diya	student	Diya Agrawal	2601ME67	2601me67@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME68	student-harshvardhan	student	Harshvardhan Kishor Shinde	2601ME68	2601me68@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME69	student-anurag-nallani	student	Anurag Nallani	2601ME69	2601me69@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME70	student-nishanth	student	Nishanth Reddy B R	2601ME70	2601me70@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME71	student-shivjeet	student	SHIVJEET KUMAR	2601ME71	2601me71@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME72	student-salunke	student	Salunke Swami Rahul	2601ME72	2601me72@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME73	student-ramavath-naik	student	Ramavath Nithin Kumar Naik	2601ME73	2601me73@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME74	student-bhukya-mohan	student	BHUKYA MOHAN	2601ME74	2601me74@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME75	student-suman	student	Suman Mondal	2601ME75	2601me75@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME76	student-rahul-raj	student	Rahul Raj	2601ME76	2601me76@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME77	student-atharv	student	Atharv Joshi	2601ME77	2601me77@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME78	student-murukuti	student	MURUKUTI SRIDHAR REDDY	2601ME78	2601me78@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME79	student-bakuri	student	Bakuri Nava Deep Raju	2601ME79	2601me79@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME80	student-gauransh	student	Gauransh Sharma	2601ME80	2601me80@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME82	student-parumandla	student	PARUMANDLA JASHWANTH	2601ME82	2601me82@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM01	student-ayush-sanjay	student	Ayush Kumar Sanjay	2601MM01	2601mm01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM02	student-vaishnavi	student	Vaishnavi L	2601MM02	2601mm02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM03	student-aakash	student	AAKASH YADAV	2601MM03	2601mm03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM04	student-anushka-ghosh	student	Anushka Ghosh	2601MM04	2601mm04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM05	student-samaksh	student	Samaksh Vishnoi	2601MM05	2601mm05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM06	student-dhanjit	student	Dhanjit Das	2601MM06	2601mm06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM07	student-deepanshu-sharma	student	DEEPANSHU SHARMA	2601MM07	2601mm07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM08	student-sumit-bisht	student	Sumit Singh Bisht	2601MM08	2601mm08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM09	student-chintalwar	student	CHINTALWAR SANKALP MUKESH	2601MM09	2601mm09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM10	student-apurva	student	Apurva Pranay	2601MM10	2601mm10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM11	student-drishti	student	Drishti	2601MM11	2601mm11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM12	student-ruhan	student	Ruhan Mazumder	2601MM12	2601mm12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM13	student-kaushik	student	Kaushik Anand	2601MM13	2601mm13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM14	student-metkar	student	METKAR PRANAV PARAG	2601MM14	2601mm14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM15	student-abhishek-2	student	ABHISHEK	2601MM15	2601mm15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM16	student-ganti	student	GANTI KOUSTHUBH	2601MM16	2601mm16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM17	student-jayant	student	Jayant Raj	2601MM17	2601mm17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM18	student-shivank-goyal	student	Shivank Goyal	2601MM18	2601mm18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM19	student-harshawardhan	student	Harshawardhan Navnath Gaikwad	2601MM19	2601mm19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM20	student-aryan-biswas	student	ARYAN BISWAS	2601MM20	2601mm20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM21	student-samarth-bajpai	student	Samarth Bajpai	2601MM21	2601mm21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM22	student-aditya-raj-2	student	Aditya Raj	2601MM22	2601mm22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM23	student-arsia	student	ARSIA	2601MM23	2601mm23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM24	student-aaranya	student	Aaranya Ganotra	2601MM24	2601mm24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM25	student-shivam-krishnan	student	Shivam Krishnan	2601MM25	2601mm25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM26	student-kuntamalla	student	KUNTAMALLA SUNIL SAI PHANINDER	2601MM26	2601mm26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM27	student-aastha	student	Aastha Mevawala	2601MM27	2601mm27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM28	student-adhyapak	student	ADHYAPAK SARTHAK JAY	2601MM28	2601mm28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM29	student-subodh	student	SUBODH SHARMA	2601MM29	2601mm29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM30	student-shyam	student	SHYAM SUNDAR GHORUI	2601MM30	2601mm30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM31	student-rizwanur	student	Rizwanur Rahman	2601MM31	2601mm31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM32	student-bhushan	student	Bhushan Vijay Barde	2601MM32	2601mm32@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM33	student-kirti	student	KIRTI VITTHAL FASATE	2601MM33	2601mm33@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM34	student-chintala	student	CHINTALA RISHITHA	2601MM34	2601mm34@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM35	student-wagmare	student	WAGMARE AJAY	2601MM35	2601mm35@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM36	student-gudala-bhanu	student	GUDALA VENKATA PRANAV BHANU	2601MM36	2601mm36@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM37	student-naitik-joshi	student	Naitik Joshi	2601MM37	2601mm37@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM38	student-rounak	student	Rounak Mandal	2601MM38	2601mm38@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM39	student-tamalika	student	TAMALIKA SAU	2601MM39	2601mm39@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM40	student-trisha	student	TRISHA SHARMA	2601MM40	2601mm40@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM41	student-chocha	student	Chocha Jaldeep palabhai	2601MM41	2601mm41@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM42	student-ayansh	student	Ayansh Pathak	2601MM42	2601mm42@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM43	student-m	student	M SIDDHARTH	2601MM43	2601mm43@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601MM44	student-ramavath-kumar	student	Ramavath Praveen Kumar	2601MM44	2601mm44@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH01	student-ankush	student	Ankush Mondal	2601PH01	2601ph01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH02	student-amit-dhakad	student	Amit dhakad	2601PH02	2601ph02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH03	student-ramavathula	student	RAMAVATHULA YATHEESWAR MANIKANTA NAIK	2601PH03	2601ph03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH04	student-aarna	student	AARNA NITI PUSHKAR	2601PH04	2601ph04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH05	student-rohan	student	ROHAN KUMAR SINGH	2601PH05	2601ph05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH06	student-aanya-2	student	Aanya	2601PH06	2601ph06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH07	student-shlok-tanmaya	student	Shlok Tanmaya	2601PH07	2601ph07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH08	student-manas	student	MANAS VERMA	2601PH08	2601ph08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH09	student-asish	student	Asish Behera	2601PH09	2601ph09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH10	student-harsh-kumar	student	Harsh Kumar	2601PH10	2601ph10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH11	student-saane	student	SAANE JYOTHSNA PRANATHI	2601PH11	2601ph11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH12	student-vedika	student	VEDIKA MILIND JAMADAR	2601PH12	2601ph12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH13	student-shaswat	student	SHASWAT GANGOPADHYAY	2601PH13	2601ph13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH14	student-ujjwal	student	Ujjwal priyedarshi	2601PH14	2601ph14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH15	student-aryan-chauhan	student	Aryan Singh Chauhan	2601PH15	2601ph15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH16	student-aditya-garg	student	Aditya Garg	2601PH16	2601ph16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH17	student-arnav-aryan	student	Arnav Aryan	2601PH17	2601ph17@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH18	student-nikhil-bharti	student	Nikhil Bharti	2601PH18	2601ph18@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH19	student-sushant	student	Sushant Jadhav	2601PH19	2601ph19@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH20	student-neha-2	student	NEHA	2601PH20	2601ph20@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH21	student-kore	student	KORE SHRIPAD RANGSIDHA	2601PH21	2601ph21@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH22	student-shreesh	student	Shreesh Srivastava	2601PH22	2601ph22@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH23	student-akhil	student	Akhil Saini	2601PH23	2601ph23@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH24	student-sivani	student	Sivani Anamika R	2601PH24	2601ph24@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH25	student-g	student	G E GURUKARTIK	2601PH25	2601ph25@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH26	student-yenuga	student	YENUGA PEDDIREDDY GARI KRISHNA	2601PH26	2601ph26@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH27	student-tisha	student	Tisha Ganvir	2601PH27	2601ph27@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH28	student-hritabrata	student	HRITABRATA SWARNAKAR	2601PH28	2601ph28@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH29	student-suraj	student	Suraj Singh	2601PH29	2601ph29@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH30	student-ponnakanti	student	PONNAKANTI VIVEK RIPUNJAY	2601PH30	2601ph30@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601PH31	student-banothu	student	Banothu Sai charan	2601PH31	2601ph31@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM01	student-patakota	student	PATAKOTA SUNAY KUMAR REDDY	2602CM01	2602cm01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM02	student-pradyumn	student	Pradyumn Jha	2602CM02	2602cm02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM03	student-lakshya-rajput	student	Lakshya Rajput	2602CM03	2602cm03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM04	student-jaiveen	student	Jaiveen Kaur	2602CM04	2602cm04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM05	student-ayansh-maurya	student	AYANSH UTKARSH MAURYA	2602CM05	2602cm05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM06	student-arhan	student	Arhan Saha	2602CM06	2602cm06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM07	student-ishant	student	Ishant	2602CM07	2602cm07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM08	student-k-sanjeevani	student	K SANJEEVANI	2602CM08	2602cm08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CM09	student-k-nayak	student	K NAVEEN NAYAK	2602CM09	2602cm09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS01	student-kakkerla	student	kakkerla pranay	2602CS01	2602cs01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS02	student-bodapati	student	BODAPATI VEERA VENKATA RAVI	2602CS02	2602cs02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS03	student-ram	student	Ram Prasannaa R	2602CS03	2602cs03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS05	student-dev-asati	student	Dev Asati	2602CS05	2602cs05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS06	student-somya	student	somya tikwani	2602CS06	2602cs06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS07	student-muniza	student	MUNIZA PARVIN	2602CS07	2602cs07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS08	student-anurag-kumar	student	Anurag Kumar	2602CS08	2602cs08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS09	student-ankit-meena	student	ANKIT MEENA	2602CS09	2602cs09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS10	student-spoorthy	student	Spoorthy M	2602CS10	2602cs10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602CS11	student-rishu	student	Rishu Kumar	2602CS11	2602cs11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT01	student-satyam-sinha	student	SATYAM SINHA	2602GT01	2602gt01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT02	student-aayush-mishra	student	Aayush Mishra	2602GT02	2602gt02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT03	student-aditya-kaushal	student	Aditya Kaushal	2602GT03	2602gt03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT04	student-daidipya	student	DAIDIPYA DADHICH	2602GT04	2602gt04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT05	student-yashraj	student	YASHRAJ JEPH	2602GT05	2602gt05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT06	student-swati	student	Swati	2602GT06	2602gt06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT07	student-rajesh	student	Rajesh	2602GT07	2602gt07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602GT08	student-raunak	student	Raunak Patel	2602GT08	2602gt08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC01	student-tushar	student	Tushar	2602MC01	2602mc01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC02	student-mudit	student	Mudit Agrawal	2602MC02	2602mc02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC03	student-abhishek-kumar-2	student	Abhishek Kumar	2602MC03	2602mc03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC04	student-raikwar	student	Raikwar Shruti Vinod	2602MC04	2602mc04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC05	student-polisetti	student	Polisetti Induja Sri Sivani	2602MC05	2602mc05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC06	student-unhone	student	Unhone Pushpak Yogesh	2602MC06	2602mc06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC07	student-potnuru-sartak	student	Potnuru Sartak	2602MC07	2602mc07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC08	student-mohammad-bohra	student	MOHAMMAD BOHRA	2602MC08	2602mc08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC09	student-v-kavin	student	V M KAVIN	2602MC09	2602mc09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MC10	student-pathlavath	student	Pathlavath Praveen Naik	2602MC10	2602mc10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT01	student-rupesh	student	Rupesh	2602MT01	2602mt01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT02	student-suhani-mehta	student	Suhani Mehta	2602MT02	2602mt02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT03	student-aryan-khambayate	student	ARYAN RAJESH KHAMBAYATE	2602MT03	2602mt03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT04	student-murthineni	student	MURTHINENI JAHNAVI NAIDU	2602MT04	2602mt04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT05	student-pratyush-srivastav	student	Pratyush Srivastav	2602MT05	2602mt05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT06	student-pratyush-srivastava	student	Pratyush Srivastava	2602MT06	2602mt06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT07	student-vadthyavath-naveen	student	VADTHYAVATH NAVEEN	2602MT07	2602mt07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT08	student-soumen	student	soumen pandit	2602MT08	2602mt08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT09	student-saksham-singh	student	Saksham Singh	2602MT09	2602mt09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602MT10	student-s-tharun	student	S K THARUN	2602MT10	2602mt10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC01	student-r	student	R SYAM SUNDAR REDDY	2602PC01	2602pc01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC02	student-mandalapu	student	Mandalapu Sai Sahasra	2602PC02	2602pc02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB11	student-karishma	student	Karishma	2501CB11	2501cb11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB12	student-pushpendra	student	Pushpendra Sharma	2501CB12	2501cb12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB13	student-abhinav	student	Abhinav B	2501CB13	2501cb13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB14	student-angaj	student	Angaj Sahil Sarjerao	2501CB14	2501cb14@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB15	student-samit	student	Samit Sardar	2501CB15	2501cb15@example.edu	2026-09-15 21:22:50.747212+00	student	t
2501CB16	student-bibhas	student	Bibhas Bikash Biswas	2501CB16	2501cb16@example.edu	2026-09-15 21:22:50.747212+00	student	t
2601ME81	student-ritu	student	ritu kumari	2601ME81	2601me81@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC03	student-rohit-behera	student	ROHIT KUMAR BEHERA	2602PC03	2602pc03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC04	student-kondaka	student	KONDAKA YASASWY	2602PC04	2602pc04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC05	student-sahil	student	Sahil	2602PC05	2602pc05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC06	student-jiya-chauhan	student	Jiya Ganeshsingh Chauhan	2602PC06	2602pc06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC07	student-anumay	student	Anumay Gupta	2602PC07	2602pc07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602PC08	student-ritesh-kumar-2	student	RITESH KUMAR	2602PC08	2602pc08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST01	student-chinmay-kumar	student	Chinmay Kumar	2602ST01	2602st01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST02	student-saptarshi-patra	student	SAPTARSHI PATRA	2602ST02	2602st02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST03	student-natasha	student	Natasha Sen	2602ST03	2602st03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST04	student-subham-kumar	student	Subham kumar	2602ST04	2602st04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST05	student-anirudh-makkapati	student	Anirudh Makkapati	2602ST05	2602st05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST06	student-pranjal-chaudhari	student	Pranjal Narendra Chaudhari	2602ST06	2602st06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST07	student-shantanu-kumar	student	SHANTANU KUMAR	2602ST07	2602st07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST08	student-vanam	student	VANAM SAI SUDEEP	2602ST08	2602st08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602ST09	student-naitik-sharma	student	Naitik Sharma	2602ST09	2602st09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL01	student-kathir	student	Kathir Selvan G	2602VL01	2602vl01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL02	student-vishnu	student	Vishnu Raj	2602VL02	2602vl02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL03	student-aryan-singh	student	Aryan singh	2602VL03	2602vl03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL04	student-andani	student	ANDANI VRAJ PINTUBHAI	2602VL04	2602vl04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL05	student-y	student	Y S Vinisha Reddy	2602VL05	2602vl05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL06	student-harshit-bajaj	student	Harshit Bajaj	2602VL06	2602vl06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL07	student-neeraj	student	Neeraj Guguloth	2602VL07	2602vl07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2602VL08	student-dhande	student	DHANDE HEMANI VINOD	2602VL08	2602vl08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603AI01	student-nagella	student	NAGELLA SHRIVATSA PRASAD	2603AI01	2603ai01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603AI02	student-nishad	student	Nishad Baviskar	2603AI02	2603ai02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603AI03	student-rahul-p	student	RAHUL PRASAD P	2603AI03	2603ai03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CB01	student-pratheeksha	student	PRATHEEKSHA B G	2603CB01	2603cb01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CB02	student-sriejan	student	Sriejan Das	2603CB02	2603cb02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CB03	student-bishu	student	Bishu Bhaskar	2603CB03	2603cb03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CB04	student-sachin-kumar	student	Sachin kumar	2603CB04	2603cb04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CE01	student-pulamolu	student	PULAMOLU JAGAN	2603CE01	2603ce01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CE02	student-vivek-singh	student	Vivek Kumar Singh	2603CE02	2603ce02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CE03	student-nikhil-singh	student	Nikhil Kumar Singh	2603CE03	2603ce03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CE04	student-bonuga	student	BONUGA KOUSHIK CHANDRA REDDY	2603CE04	2603ce04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CE05	student-akshadha	student	AKSHADHA RAMKUMAR	2603CE05	2603ce05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CE06	student-ayush-singh	student	Ayush Singh	2603CE06	2603ce06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CS01	student-alankrit	student	Alankrit Patel	2603CS01	2603cs01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CS02	student-champa	student	Champa Yeshey	2603CS02	2603cs02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CS03	student-kalpit	student	Kalpit Thakur	2603CS03	2603cs03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CT01	student-mithil	student	MITHIL MANISH PARCHURE	2603CT01	2603ct01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CT02	student-srimahi	student	Srimahi Reddy Yeltiwar	2603CT02	2603ct02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CT03	student-dipu	student	Dipu Kumar Kewat	2603CT03	2603ct03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603CT04	student-kishan-bhava	student	Kishan Jothi Bhava	2603CT04	2603ct04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603EC01	student-aditya-bhagat	student	ADITYA KUMAR BHAGAT	2603EC01	2603ec01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603EC02	student-kaushik-kumar	student	Kaushik Kumar	2603EC02	2603ec02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603EE01	student-jasmeet	student	JASMEET SINGH	2603EE01	2603ee01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603EE02	student-arshita	student	Arshita Agarwal	2603EE02	2603ee02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603EE03	student-lakshmi-paladugu	student	LAKSHMI REVANTH SAI PALADUGU	2603EE03	2603ee03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603EE04	student-putluru	student	PUTLURU SAI VARSHITH REDDY	2603EE04	2603ee04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603EE05	student-abhinav-anand	student	Abhinav Anand	2603EE05	2603ee05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ES01	student-ramchandra	student	Ramchandra Tholiya	2603ES01	2603es01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ES02	student-thorat	student	THORAT DAKSH	2603ES02	2603es02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ES03	student-pranil	student	PRANIL NIKHIL DUBE	2603ES03	2603es03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ES04	student-rachit-agarwal	student	Rachit Agarwal	2603ES04	2603es04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MC01	student-gurkeerat	student	GURKEERAT SINGH	2603MC01	2603mc01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MC02	student-barukunta	student	Barukunta Sankeerth	2603MC02	2603mc02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MC03	student-rashmita	student	Rashmita yadav	2603MC03	2603mc03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME01	student-pranjal-nerkar	student	Pranjal Prashant Nerkar	2603ME01	2603me01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME02	student-karwar	student	KARWAR VEDANT DATTATRAY	2603ME02	2603me02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME03	student-poorvanjali	student	Poorvanjali	2603ME03	2603me03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME04	student-vikash	student	Vikash Vaibhav	2603ME04	2603me04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME05	student-sarda	student	Sarda Dhruv	2603ME05	2603me05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME06	student-mitadru	student	MITADRU KAR	2603ME06	2603me06@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME07	student-biroju	student	BIROJU RUSHIKESH	2603ME07	2603me07@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME08	student-rohit-choudhary	student	Rohit Choudhary	2603ME08	2603me08@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME09	student-parikshit	student	Parikshit Bedi	2603ME09	2603me09@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME10	student-moulik	student	Moulik Singh	2603ME10	2603me10@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME11	student-donapati	student	Donapati Dhruva Kumar Reddy	2603ME11	2603me11@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME12	student-nityasri	student	NITYASRI A	2603ME12	2603me12@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603ME13	student-silimkar	student	Silimkar Tejas Mangesh	2603ME13	2603me13@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MM01	student-mayank-2	student	Mayank	2603MM01	2603mm01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MM02	student-ritojoy	student	Ritojoy Mandal	2603MM02	2603mm02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MM03	student-banavath-manoj	student	BANAVATH MANOJ	2603MM03	2603mm03@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MM04	student-adya	student	Adya Agarwal	2603MM04	2603mm04@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603MM05	student-telugu	student	TELUGU SHASHANK	2603MM05	2603mm05@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603PH01	student-aryan-aggrawal	student	Aryan Aggrawal	2603PH01	2603ph01@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603PH02	student-arka	student	ARKA DAS	2603PH02	2603ph02@example.edu	2026-09-15 21:22:50.747212+00	student	t
2603PH03	student-mahak-shakya	student	Mahak Shakya	2603PH03	2603ph03@example.edu	2026-09-15 21:22:50.747212+00	student	t
\.


--
-- Name: complaint_history complaint_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_history
    ADD CONSTRAINT complaint_history_pkey PRIMARY KEY (id);


--
-- Name: complaints complaints_complaint_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT complaints_complaint_number_key UNIQUE (complaint_number);


--
-- Name: complaints complaints_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT complaints_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_roll_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_roll_number_key UNIQUE (roll_number);


--
-- Name: idx_complaint_history_complaint_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaint_history_complaint_id ON public.complaint_history USING btree (complaint_id, created_at);


--
-- Name: idx_complaints_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_category ON public.complaints USING btree (lower((category)::text));


--
-- Name: idx_complaints_category_completed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_category_completed ON public.complaints USING btree (lower((category)::text), completed_at DESC) WHERE ((status)::text = 'COMPLETED'::text);


--
-- Name: idx_complaints_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_created_at ON public.complaints USING btree (created_at DESC);


--
-- Name: idx_complaints_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_status ON public.complaints USING btree (status);


--
-- Name: idx_complaints_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_complaints_user_id ON public.complaints USING btree (user_id);


--
-- Name: uniq_open_complaints; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uniq_open_complaints ON public.complaints USING btree (lower((category)::text), lower(btrim(title)), md5(lower(btrim(description)))) WHERE ((status)::text = ANY ((ARRAY['PENDING_VERIFICATION'::character varying, 'PROGRESS'::character varying])::text[]));


--
-- Name: complaints trg_prune_completed_complaints; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_prune_completed_complaints AFTER INSERT OR UPDATE OF status ON public.complaints FOR EACH ROW WHEN (((new.status)::text = 'COMPLETED'::text)) EXECUTE FUNCTION public.prune_old_completed_complaints();


--
-- Name: users trg_users_roll_number_to_id; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_users_roll_number_to_id BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.users_set_roll_number_to_id();


--
-- Name: complaint_history complaint_history_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_history
    ADD CONSTRAINT complaint_history_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id);


--
-- Name: complaint_history complaint_history_complaint_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaint_history
    ADD CONSTRAINT complaint_history_complaint_id_fkey FOREIGN KEY (complaint_id) REFERENCES public.complaints(id) ON DELETE CASCADE;


--
-- Name: complaints complaints_completed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT complaints_completed_by_fkey FOREIGN KEY (completed_by) REFERENCES public.users(id);


--
-- Name: complaints complaints_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT complaints_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: complaints complaints_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.complaints
    ADD CONSTRAINT complaints_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict GOoOLfiqxltfWuRe0ANC6ST8D1ADhONaz2mn43tG5VtdaYO46jAAINcEiJSzID0


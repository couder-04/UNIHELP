--
-- PostgreSQL database dump
--

\restrict ldgjGALhvETQks6wgu3PUaMdPrboiGCvPUMQkwPexjYljz7pOy8yf72yRlBlMTv

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

ALTER TABLE IF EXISTS ONLY public.notices DROP CONSTRAINT IF EXISTS notices_pkey;
DROP TABLE IF EXISTS public.notices;
DROP EXTENSION IF EXISTS pgcrypto;
--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: notices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    publish_timestamp timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    content text NOT NULL,
    notice_type character varying(100) NOT NULL,
    author_id character varying(255) NOT NULL,
    author_authority character varying(100) NOT NULL,
    target_audience text[] NOT NULL,
    status character varying(50) DEFAULT 'Active'::character varying,
    expires_at timestamp with time zone
);


--
-- Data for Name: notices; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notices (id, publish_timestamp, content, notice_type, author_id, author_authority, target_audience, status, expires_at) FROM stdin;
\.


--
-- Name: notices notices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notices
    ADD CONSTRAINT notices_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict ldgjGALhvETQks6wgu3PUaMdPrboiGCvPUMQkwPexjYljz7pOy8yf72yRlBlMTv


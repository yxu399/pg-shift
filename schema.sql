--
-- PostgreSQL database dump
--

\restrict b4YfvAwZGaM43wV9HKvPsgnevNTSPa7iYWj0p4iBL03cFyBZvUyvjBKEQLuwpAL

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 15.15 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: big_data_table; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.big_data_table (
    id integer NOT NULL,
    user_email text NOT NULL
);


--
-- Name: big_data_table_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.big_data_table_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: big_data_table_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.big_data_table_id_seq OWNED BY public.big_data_table.id;


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    checksum character varying(64) NOT NULL,
    applied_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    batch integer DEFAULT 1 NOT NULL
);


--
-- Name: test_tx; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test_tx (
    id integer NOT NULL
);


--
-- Name: test_tx_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.test_tx_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: test_tx_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.test_tx_id_seq OWNED BY public.test_tx.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: big_data_table id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.big_data_table ALTER COLUMN id SET DEFAULT nextval('public.big_data_table_id_seq'::regclass);


--
-- Name: test_tx id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_tx ALTER COLUMN id SET DEFAULT nextval('public.test_tx_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: big_data_table big_data_table_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.big_data_table
    ADD CONSTRAINT big_data_table_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: test_tx test_tx_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_tx
    ADD CONSTRAINT test_tx_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_test_tx_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_test_tx_id ON public.test_tx USING btree (id);


--
-- PostgreSQL database dump complete
--

\unrestrict b4YfvAwZGaM43wV9HKvPsgnevNTSPa7iYWj0p4iBL03cFyBZvUyvjBKEQLuwpAL


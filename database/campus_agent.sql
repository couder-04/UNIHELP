--
-- PostgreSQL database dump
--

\restrict 70XtgJeSimh3yPjHcCvUg8Ty5ZdYpclukPDlSAPdQJoL8SWrygMWVmiP7QdQZXY

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

ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_roll_number_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
DROP TABLE IF EXISTS public.users;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    authentication_key character varying NOT NULL,
    role character varying NOT NULL,
    names text NOT NULL,
    roll_number text NOT NULL,
    CONSTRAINT users_role_check CHECK ((lower((role)::text) = ANY (ARRAY['student'::text, 'faculty'::text, 'admin'::text])))
);


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (authentication_key, role, names, roll_number) FROM stdin;
student-j	student	J Samrutha	2501CB01
student-priyanshi	student	Priyanshi Patel	2501CB02
student-dia	student	Dia Halder	2501CB03
student-emin	student	Emin Philip Saji	2501CB04
student-kajal	student	Kajal Batra	2501CB05
student-archit	student	Archit Shanker	2501CB06
faculty-demo	faculty	Priya Patel	PF001
admin-demo	admin	Rohan Verma	AD001
student-jarpula	student	Jarpula Murali	2501CB07
student-manav	student	Manav Rathore	2501CB08
student-ananya	student	Ananya Iyer	2501AI51
student-saptarshi	student	Saptarshi Bose	2501CB09
faculty-arjun	faculty	Arjun Nair	PF002
faculty-meera	faculty	Meera Joshi	PF003
faculty-sameer	faculty	Sameer Khan	PF004
faculty-kavita	faculty	Kavita Desai	PF005
faculty-aditi	faculty	Aditi Rao	PF006
faculty-harsh	faculty	Harsh Vardhan	PF007
faculty-leela	faculty	Leela Menon	PF008
faculty-omar	faculty	Omar Qureshi	PF009
faculty-tanvi	faculty	Tanvi Shah	PF010
faculty-nikhil	faculty	Nikhil Rao	PF011
faculty-pooja	faculty	Pooja Bhatt	PF012
faculty-farhan	faculty	Farhan Ali	PF013
faculty-diya	faculty	Diya Kulkarni	PF014
faculty-yash	faculty	Yash Agarwal	PF015
faculty-sana	faculty	Sana Iqbal	PF016
admin-nisha	admin	Nisha Kapoor	AD002
student-katuri	student	Katuri Vanshika	2501CB10
student-karishma	student	Karishma	2501CB11
student-pushpendra	student	Pushpendra Sharma	2501CB12
student-abhinav	student	Abhinav B	2501CB13
student-angaj	student	Angaj Sahil Sarjerao	2501CB14
student-samit	student	Samit Sardar	2501CB15
student-bibhas	student	Bibhas Bikash Biswas	2501CB16
student-vaibhav	student	Vaibhav Sanjay Bhagure	2501CB17
student-vansh	student	Vansh Khurana	2501CB18
student-dhruv	student	Dhruv Agnihotri	2501CB19
student-oshi	student	Oshi Malviya	2501CB20
student-nasreen	student	Nasreen Fatima	2501CB21
student-dhruv-ganatra	student	Dhruv Arvind Ganatra	2501CB22
student-aarsh	student	Aarsh Jain	2501CB23
student-dhadse	student	Dhadse Omesh Vasantrao	2501CB24
student-vaanya	student	Vaanya Verma	2501CB25
student-aryan	student	Aryan Dev	2501CB26
student-vaishnav	student	Vaishnav Krishna Durgasi	2501CB27
student-shantanu	student	Shantanu Sardar	2501CB28
student-kavya	student	Kavya Gupta	2501CB29
student-swarnava	student	Swarnava Kundu	2501CB30
student-hemant	student	Hemant Kumar Bairwa	2501CB31
student-biki	student	Biki Barman	2501CB32
student-abhishek	student	Abhishek Bansal	2501CB33
student-anser	student	Anser Ayaan	2501CB34
student-s	student	S Aditya	2501CB35
student-vadavelli	student	Vadavelli Kamali Harshitha	2501CB36
student-anupam	student	Anupam Sharma	2501CB37
student-sai	student	Sai Subrat Jena	2501CB38
student-aman	student	Aman Saroj	2501CB39
student-gaurav	student	Gaurav Sukhadia	2501CB40
student-avdhesh	student	Avdhesh Meena	2501CB41
student-ahan	student	Ahan Bhattacharjee	2501CB42
student-madhur	student	Madhur Srivastava	2501CB43
student-sakala	student	Sakala Sathwik	2501CB44
student-pilli	student	Pilli Sri Vaishnavi	2501CB45
student-chilmakuri	student	Chilmakuri Charan	2501CB46
student-hariom	student	Hariom Singh	2501CB47
student-mada	student	Mada Akeera Sri Varshan	2501CB48
student-abhi	student	Abhi Raj	2501CB49
student-raushan	student	Raushan Kumar	2501CB50
student-boyina	student	Boyina Sadvika	2501CB51
student-sarthak	student	Sarthak Anusimi	2501CB52
student-sanket	student	Sanket Yadav Jadhav	2501CB53
student-riddhi	student	Riddhi Patel	2501CB54
student-sachin	student	Sachin	2501CB55
student-raj	student	Raj Aryan	2501CB56
student-raghvendra	student	Raghvendra Meena	2501CB57
student-adwait	student	Adwait Vats	2501CB58
student-snehadip	student	Snehadip Ghosh	2501CB59
student-biswas	student	Biswas Mayank Pradyut	2501CB60
student-satish	student	Satish Kumar Yadav	2501CB61
student-anshu	student	Anshu Vishwakarma	2501CB62
student-taniya	student	Taniya Kumari Gupta	2501CB63
student-shorya	student	Shorya Pratap Singh	2501CB64
student-vadithya	student	Vadithya Upendar	2501CB65
student-peruru	student	Peruru Snigdha Reddy	2501CS01
student-kummara	student	Kummara Jyothi Prajwal	2501CS02
student-choudavarapu	student	Choudavarapu Snehan	2501CS03
student-megh	student	Megh Dhaval Parikh	2501CS04
student-pranjal	student	Pranjal Kukreja	2501CS05
student-tata	student	Tata Jayanth Naga Sai	2501CS06
student-aayush	student	Aayush Raj	2501CS07
student-ritesh	student	Ritesh	2501CS08
student-demo	student	Aarav Sharma	2501CS09
student-shushant	student	Shushant	2501CS10
student-bhukya	student	Bhukya Pavan Kumar	2501CS11
student-manish	student	Manish Sharma	2501CS12
student-shreya	student	Shreya Kumari	2501CS13
student-keshav	student	Keshav Jha	2501CS14
student-chitra	student	Chitra Sandilya	2501CS15
student-sachin-gautam	student	Sachin Gautam	2501CS16
student-prashant	student	Prashant Kumar	2501CS17
student-sabavath	student	Sabavath Aishwarya Chouhan	2501CS18
student-aditya	student	Aditya Kumar	2501CS19
student-ayush	student	Ayush Anand	2501CS20
student-shristi	student	Shristi Kumari	2501CS21
student-vijayanagaram	student	Vijayanagaram Sreethi	2501CS22
student-suzal	student	Suzal	2501CS23
student-parth	student	Parth Tomar	2501CS24
student-kotollu	student	Kotollu Neharika	2501CS25
student-gaurav-choudhury	student	Gaurav Choudhury	2501CS26
student-bartika	student	Bartika Kumar	2501CS27
student-gunturu	student	Gunturu Srikanth	2501CS28
student-pola	student	Pola Hymavathi	2501CS29
student-affan	student	Affan Mushtaque	2501CS30
student-jangiti	student	Jangiti Sathwik Kumar	2501CS31
student-anushtup	student	Anushtup Kumar	2501CS32
student-gandhe	student	Gandhe Sahasra	2501CS33
student-anushka	student	Anushka Nayak	2501CS34
student-rajiv	student	Rajiv Kumar Karn	2501CS35
student-abhirup	student	Abhirup Dhara	2501CS36
student-akshay	student	Akshay Kulkarni	2501CS37
student-jakkula	student	Jakkula Udayasree	2501CS38
student-harshil	student	Harshil Chukkala	2501CS39
student-anuj	student	Anuj Omprakash Pupal	2501CS40
student-mekala	student	Mekala Uday Kiran	2501CS41
student-shivam	student	Shivam Kapoor	2501CS42
student-kasireddy	student	Kasireddy Sri Charan	2501CS43
student-aryan-kumar	student	Aryan Kumar	2501CS44
student-guguloth	student	Guguloth Arun	2501CS45
student-pranay	student	Pranay Bansal	2501CS46
student-somu	student	Somu Nitin Deeraj Anja	2501CS47
student-bikesh	student	Bikesh Loonaich	2501CS48
student-mukka	student	Mukka Anjani Koumudh	2501CS49
student-chinthareddy	student	Chinthareddy Varun Te	2501CS50
student-ojasvee	student	Ojasvee Vatsa	2501CS51
student-aman-gautam	student	Aman Gautam	2501CS52
student-yash	student	Yash Trivedi	2501CS53
student-gade	student	Gade Chandan	2501CS54
student-bedabrata	student	Bedabrata Ghosh	2501CS55
student-pinakpani	student	Pinakpani Mandal	2501CS56
student-ishan	student	Ishan Kumar	2501CS57
student-kalathiya	student	Kalathiya Priyank Palak	2501CS58
student-angel	student	Angel Mahi Sharma	2501CS59
student-kunal	student	Kunal Raj	2501CS60
student-rahul	student	Rahul Kumar	2501CS61
student-shivam-kumar	student	Shivam Kumar	2501CS62
student-neeradi	student	Neeradi Thanmai	2501CS63
student-ravi	student	Ravi Raj Prasad	2501CS64
student-mylavarapu	student	Mylavarapu Vivek	2501CS65
student-nelluri	student	Nelluri Sai Sri Harsha	2501CS66
student-ishan-srivastava	student	Ishan Srivastava	2501CS67
student-nihal	student	Nihal Saini	2501CS68
student-amit	student	Amit Sunil Ahirrao	2501CS69
student-kimidi	student	Kimidi Pardhiv	2501CS70
student-vishesh	student	Vishesh Agrawal	2501CS71
student-parnapalli	student	Parnapalli Avulannagar	2501CS72
student-shinde	student	Shinde Siddham Subha	2501CS73
student-aditya-raj	student	Aditya Raj	2501CS74
student-yenninti	student	Yenninti Laxman	2501CS75
student-pratyay	student	Pratyay Garg	2501CS76
student-katravath	student	Katravath Vinod	2501CS77
student-ishan-alam	student	Ishan Alam	2501CS78
student-vittal	student	Vittal Das A	2501CS79
student-mohit	student	Mohit Kumar	2501CS80
student-shivank	student	Shivank Man	2501CS81
student-ansh	student	Ansh Motghare	2501CS82
student-mohit-peswani	student	Mohit Peswani	2501CS83
student-vikki	student	Vikki Kumar	2501CS85
student-smruti	student	Smruti Ranjan Sahu	2501CS86
student-kuldeep	student	Kuldeep Kumar Roy	2501CS87
student-lutta	student	Lutta Ananya	2501CS88
student-goutam	student	Goutam Kumar Ghosal	2501CS89
student-neha	student	Neha Gupta	2501CS90
student-kabir	student	Kabir Mehta	2501CS91
student-vikram	student	Vikram Singh	2501CS92
student-arnav	student	Arnav Rastogi	2502CS01
student-baibhaw	student	Baibhaw Kumar	2502CS02
student-shubham	student	Shubham	2502CS03
student-kartik	student	Kartik Jitendra Tetwar	2502CS04
student-daksh	student	Daksh Mittal	2502CS05
student-pratyush	student	Pratyush Singh	2502CS06
student-kondala	student	Kondala Rushi Teja	2502CS07
student-mahak	student	Mahak Banyala	2502CS08
student-mohd	student	Mohd Shuaib	2502CS09
student-adarsh	student	Adarsh Choudhary	2503CB01
student-amoolya	student	Amoolya Sharan	2503CB02
student-tejveer	student	Tejveer	2503CB03
student-yash-madhok	student	Yash Madhok	2503CB04
student-dheeraj	student	Dheeraj Kumar	2503CB05
student-sourav	student	Sourav Bhakat	2503CS01
student-meer	student	Meer Riteshkumar Kapadia	2503CS02
student-digvijay	student	Digvijay Suresh Zarekar	2503CS03
student-aniska	student	Aniska Saha	2503CS04
student-guguloth-kumar	student	Guguloth Venu Kumar	2503CS05
student-nukala	student	NUKALA VENKATA CHANDRAHAS	2601AI01
student-annamanani	student	ANNAMANANI ASHWADH	2601AI02
student-yeruva	student	YERUVA PRAHARSHINI	2601AI03
student-kanak	student	Kanak Agrawal	2601AI04
student-bhavya	student	Bhavya Rathi	2601AI05
student-jatothu	student	JATOTHU SAI CHAITANYA	2601AI06
student-aryan-gautam	student	Aryan Gautam	2601AI07
student-aditya-parmar	student	ADITYA PARMAR	2601AI08
student-priyanshu	student	Priyanshu	2601AI09
student-radhika	student	Radhika	2601AI10
student-aanya	student	Aanya Choudhary	2601AI11
student-mayank	student	Mayank Sharma	2601AI12
student-mereddy	student	Mereddy Neha Reddy	2601AI13
student-harshit	student	Harshit Kumar	2601AI14
student-mulkala	student	MULKALA VASHISTA	2601AI15
student-aditi	student	ADITI VERMA	2601AI16
student-gudala	student	GUDALA YOZAN BABU	2601AI17
student-saujanya	student	Saujanya Singh	2601AI18
student-potnuru	student	POTNURU MURALI SRI KRISHNA	2601AI19
student-yash-2	student	Yash	2601AI20
student-gundu	student	GUNDU HARDIK	2601AI21
student-modadugu	student	MODADUGU VENKATA SAI SIVA	2601AI22
student-abhikshit	student	Abhikshit Singh	2601AI23
student-viraj	student	Viraj Singh	2601AI24
student-aditya-thakur	student	ADITYA THAKUR	2601AI25
student-samyaraj	student	Samyaraj Pal	2601AI26
student-omdeep	student	OMDEEP SARKAR	2601AI27
student-patel	student	PATEL LOKESH	2601AI28
student-rahane	student	Rahane Anish Sanjay	2601AI29
student-vanapalli	student	VANAPALLI YASASWINI	2601AI30
student-mamidi	student	MAMIDI VISHNU VARDHAN	2601AI31
student-kandibanda	student	Kandibanda Nehal	2601AI32
student-lakavath	student	LAKAVATH SANTHOSH	2601AI33
student-kuldeep-vaghamshi	student	Kuldeep Vaghamshi	2601AI34
student-anubhav	student	ANUBHAV HIMATSINGKA	2601AI35
student-sachin-prakash	student	Sachin Prakash	2601AI36
student-voni	student	Voni srivalli	2601AI37
student-amara	student	AMARA DURGA VENKATA DHEERAJ	2601AI38
student-kratarth	student	Kratarth Shrivastava	2601AI39
student-kesugani	student	Kesugani Pranay Dev Maharaj	2601AI40
student-gumpu	student	GUMPU PUNEETH SASANK	2601AI41
student-kollu	student	Kollu Venkata Abhinash	2601AI42
student-parlapalli	student	PARLAPALLI SURYA SRIKAR REDDY	2601AI43
student-tokalwad	student	Tokalwad Parth Anand	2601AI44
student-anushka-gupta	student	ANUSHKA GUPTA	2601AI45
student-palakonda	student	PALAKONDA RITVIKREDDY	2601AI46
student-ashish	student	ASHISH KUMAR	2601AI47
student-kada	student	Kada Darshan	2601AI48
student-yepparika	student	YEPPARIKA TEJASWANTH	2601AI49
student-sarthak-kumar	student	Sarthak Kumar	2601AI50
student-gargi	student	Gargi	2601AI51
student-shorya-sharma	student	SHORYA SHARMA	2601CB01
student-aditi-kumari	student	Aditi Kumari	2601CB02
student-animesh	student	Animesh Kumar Jha	2601CB03
student-rathod	student	Rathod Rithesh	2601CB04
student-siriki	student	Siriki Hemanth	2601CB05
student-anshul	student	Anshul Tyagi	2601CB06
student-kota	student	KOTA MANIDEEP	2601CB07
student-adarsh-mohanty	student	Adarsh Mohanty	2601CB08
student-manash	student	MANASH KACHARI	2601CB09
student-krishna	student	KRISHNA SARDAR	2601CB10
student-jeetesh	student	Jeetesh kumar sahu	2601CB11
student-utkarsh	student	UTKARSH YADAV	2601CB12
student-ishan-saraswat	student	Ishan Saraswat	2601CB13
student-tej	student	Tej Pratap	2601CB14
student-dipesh	student	Dipesh Prajapat	2601CB15
student-shreyas	student	Shreyas Gaurav Tarway	2601CB16
student-shourya	student	Shourya Pandey	2601CB17
student-ishita	student	Ishita Singh	2601CB18
student-abhinaba	student	ABHINABA GHOSH	2601CB19
student-agniva	student	Agniva Biswas	2601CB20
student-jharana	student	Jharana Lathigara	2601CB21
student-adway	student	Adway Vijay Shinde	2601CB22
student-ujwal	student	UJWAL KUMAR JHA	2601CB23
student-ayush-gupta	student	Ayush Gupta	2601CB24
student-tanushka	student	Tanushka Sharma	2601CB25
student-swarit	student	Swarit Srivastava	2601CB26
student-sameer	student	Sameer Kardam	2601CB27
student-yadlapalli	student	Yadlapalli Sahiti	2601CB28
student-gaurav-agnihotri	student	Gaurav Agnihotri	2601CB29
student-mohammad	student	MOHAMMAD IBRAHIM	2601CB30
student-samarth	student	Samarth Pratap Singh	2601CB31
student-satyam	student	SATYAM KUMAR KASHYAP	2601CB32
student-ranveer	student	Ranveer Raj	2601CB33
student-yogeshwar	student	Yogeshwar Singh	2601CB34
student-abhay	student	Abhay Yadav	2601CB35
student-nikhil	student	Nikhil Sonkar	2601CB36
student-omraj	student	OMRAJ KUMAR	2601CB37
student-khushi	student	Khushi Kishor Paulbudhe	2601CB38
student-satyam-kumar	student	Satyam Kumar	2601CB39
student-tanay	student	Tanay Sanghvi	2601CB40
student-wathore	student	WATHORE HARSH DATTA	2601CB41
student-abhinav-singh	student	ABHINAV SINGH	2601CB42
student-ayush-raj	student	Ayush Raj	2601CB43
student-soham	student	Soham Ghosh	2601CB44
student-aditya-gupta	student	Aditya Gupta	2601CB45
student-shobhit	student	Shobhit airan	2601CB46
student-nasir	student	Nasir Raza	2601CB47
student-jitin	student	JITIN KUMAR	2601CB48
student-shubhi	student	Shubhi Jain	2601CB49
student-pushpraj	student	Pushpraj Nigwal	2601CB50
student-akula	student	AKULA ANJANA SOWMYA	2601CB51
student-shagun	student	Shagun Singh	2601CB52
student-nikhil-2	student	NIKHIL	2601CB53
student-pintu	student	Pintu Mondal	2601CB54
student-varahi	student	Varahi Rohit Pardeshi	2601CB55
student-mudavath	student	MUDAVATH DIVYA	2601CB56
student-sharad	student	Sharad Rajesh Namdeo	2601CB57
student-umesh	student	Umesh Soni	2601CB58
student-illa	student	ILLA RAMYA	2601CB59
student-lohit	student	lohit s	2601CB60
student-ankit	student	Ankit Kumar Subai	2601CB61
student-sampathi	student	SAMPATHI MAYANK	2601CB62
student-gyanvi	student	Gyanvi Priya	2601CB63
student-peddaram	student	Peddaram Sahasra Vardhini	2601CB64
student-gangapatnam	student	gangapatnam shyam abhishek	2601CB65
student-guguloth-shekar	student	GUGULOTH SHEKAR	2601CB66
student-kevlani	student	Kevlani Yash Manishbhai	2601CB67
student-om	student	Om Parth	2601CE01
student-mahi	student	Mahi Agrawal	2601CE02
student-nishant	student	Nishant Singh	2601CE03
student-kurva	student	KURVA ABHISHEK	2601CE04
student-vipin	student	VIPIN KUMAR	2601CE05
student-priyamgaurvi	student	Priyamgaurvi	2601CE06
student-pratham	student	Pratham Singla	2601CE07
student-animesh-shukla	student	Animesh Shukla	2601CE08
student-kishan	student	KISHAN KUMAR	2601CE09
student-anupam-jha	student	Anupam Jha	2601CE10
student-harsh	student	HARSH PRATAP SINGH	2601CE11
student-aarju	student	Aarju	2601CE12
student-chetan	student	Chetan Singh	2601CE13
student-anand	student	Anand Kumar	2601CE14
student-snigdh	student	Snigdh Arindam	2601CE15
student-arpit	student	ARPIT MISHRA	2601CE16
student-vivek	student	VIVEK GOYAL	2601CE17
student-arya	student	Arya Deshmukh	2601CE18
student-gajendra	student	GAJENDRA KUMAR JAT	2601CE19
student-rahul-nagora	student	Rahul Nagora	2601CE20
student-harsh-saini	student	Harsh Saini	2601CE21
student-dharamveer	student	Dharamveer pingoliya	2601CE22
student-dasu	student	Dasu Jayasree	2601CE23
student-saumya	student	SAUMYA SHARMA	2601CE24
student-rishabh	student	RISHABH SINGH	2601CE25
student-ameya	student	AMEYA PRAVIN KAMAT	2601CE26
student-sarthak-samanta	student	SARTHAK KUMAR DHIR SAMANTA	2601CE27
student-tammireddi	student	TAMMIREDDI PRANATHI	2601CE28
student-prashant-meena	student	Prashant meena	2601CE29
student-rakesh	student	Rakesh Jangid	2601CE30
student-vivek-meena	student	Vivek meena	2601CE31
student-sudhanshu	student	SUDHANSHU SANJAY AJGAONKAR	2601CE32
student-atul	student	ATUL BARWAL	2601CE33
student-sabavat	student	SABAVAT AISHWARYA	2601CE34
student-vaibhav-anand	student	VAIBHAV ANAND	2601CE35
student-sarvjeet	student	Sarvjeet Kumar	2601CE36
student-aanya-verma	student	aanya verma	2601CE37
student-aryan-rai	student	Aryan Rai	2601CE38
student-wriddhi	student	Wriddhi Adhya	2601CE39
student-pritam	student	Pritam Kumar Siddhant	2601CE40
student-balajii	student	Balajii Jha	2601CE41
student-aditya-singh	student	Aditya Singh	2601CE42
student-mohammad-kamran	student	MOHAMMAD KAMRAN	2601CE43
student-shivam-raj	student	SHIVAM RAJ	2601CE44
student-pradip	student	PRADIP KUMAR	2601CE45
student-harsh-sharma	student	Harsh Sharma	2601CE46
student-shreya-kumari	student	Shreya Kumari	2601CE47
student-gurram	student	GURRAM AKSHARA	2601CE48
student-vaibhav-pankaj	student	Vaibhav Pankaj	2601CE49
student-shaik	student	Shaik Arbaaz Ahmed	2601CE50
student-ahon	student	Ahon Pansa	2601CE51
student-vankudoth	student	VANKUDOTH RAMCHARAN	2601CE52
student-harshit-mangal	student	Harshit Mangal	2601CE53
student-mahi-khera	student	Mahi Khera	2601CE54
student-deepak	student	Deepak Singh	2601CE55
student-lokesh	student	Lokesh yadav	2601CE56
student-abhijeet	student	Abhijeet Kumar	2601CE57
student-anurag	student	Anurag Jha	2601CE58
student-jatin	student	Jatin	2601CE59
student-gaurav-kumar	student	GAURAV KUMAR	2601CE60
student-yogendra	student	YOGENDRA KUMAR RAWAT	2601CE61
student-aman-kumar	student	Aman Kumar	2601CE62
student-rohit	student	Rohit dulariya	2601CE63
student-tholisaku	student	Tholisaku sruthi	2601CE64
student-vadthyavath	student	VADTHYAVATH BHUVANENDRA NAIK	2601CS01
student-gajendra-sarathe	student	Gajendra Sarathe	2601CS02
student-daksh-joshi	student	Daksh Joshi	2601CS03
student-aryan-raj	student	Aryan Raj	2601CS04
student-jakkampudi	student	Jakkampudi Tanuj	2601CS05
student-aditya-negi	student	Aditya Negi	2601CS06
student-khushi-agrawal	student	Khushi Agrawal	2601CS07
student-shubhkarmandeep	student	Shubhkarmandeep Singh	2601CS08
student-parminder	student	Parminder Mittal	2601CS09
student-vankunavath	student	Vankunavath Shashank Indra tej	2601CS10
student-yogyta	student	YOGYTA VERMA	2601CS11
student-mohammad-husain	student	Mohammad Husain	2601CS12
student-varanasi	student	varanasi abhiram	2601CS13
student-shivam-sahoo	student	SHIVAM SAHOO	2601CS14
student-narottam	student	Narottam Singh Sikarwar	2601CS15
student-biswajit	student	Biswajit Sahoo	2601CS16
student-gotam	student	Gotam	2601CS17
student-vekariya	student	Vekariya Smit Naranbhai	2601CS18
student-gajibelli	student	GAJIBELLI PUSHPA VAMSI	2601CS19
student-garv	student	Garv Singh Gaharwar	2601CS20
student-ankit-mishra	student	ANKIT MISHRA	2601CS21
student-kalluru	student	KALLURU DEEKSHITHA REDDY	2601CS22
student-shristy	student	Shristy Kumari	2601CS23
student-jadhav	student	JADHAV PRAJYOT	2601CS24
student-bhujuti	student	BHUJUTI BILVIKA	2601CS25
student-pratik	student	Pratik Rajabapu Kesbhat	2601CS26
student-talasani	student	Talasani Rithwik Reddy	2601CS27
student-jeswanth	student	JESWANTH C S	2601CS28
student-patibandla	student	PATIBANDLA AKASH	2601CS29
student-mudokulam	student	MUDOKULAM JAIKISHAN NAIK	2601CS30
student-utkarsh-raj	student	Utkarsh Raj	2601CS31
student-k	student	K Rahul Kumar reddy	2601CS32
student-aditya-singh-2	student	Aditya Singh	2601CS33
student-kuluri	student	kuluri venkata sai kaushik	2601CS34
student-neralwar	student	NERALWAR CHAANAKYA DAAMAN	2601CS35
student-avinash	student	Avinash Shakya	2601CS36
student-grisha	student	Grisha Garg	2601CS37
student-rishabh-rai	student	Rishabh Rai	2601CS38
student-kurupudi	student	kurupudi sai sathvika	2601CS39
student-raghav	student	RAGHAV JESANI	2601CS40
student-v	student	V VARUNKUMAR	2601CS41
student-krishna-kumar	student	Krishna Kumar	2601CS42
student-dhruv-2	student	Dhruv	2601CS43
student-poura	student	Poura Venkata Bhavesh	2601CS44
student-aditya-kashyap	student	Aditya Kashyap	2601CS45
student-darshana	student	Darshana Rawatale	2601CS46
student-pramod	student	PRAMOD YADAV	2601CS47
student-karan	student	Karan Rajput	2601CS48
student-lapshetwar	student	LAPSHETWAR SHIVAM PRADIP	2601CS49
student-abhishek-kumar	student	Abhishek Kumar	2601CS50
student-kottisa	student	KOTTISA NIKHITH	2601CS51
student-shivansh	student	Shivansh Tripathi	2601CS52
student-ayushman	student	Ayushman Ghatak	2601CS53
student-harsh-patel	student	harsh patel	2601CS54
student-kethireddy	student	kethireddy Nagapuneeth Reddy	2601CS55
student-suhani	student	Suhani Gulati	2601CS56
student-vemu	student	Vemu Manjula	2601CS57
student-aamana	student	AAMANA KHATOON	2601CS58
student-katrodiya	student	KATRODIYA PRINCE BIPIN	2601CS59
student-yashas	student	Yashas Prasanna	2601CS60
student-dhondre	student	Dhondre Soniya Ganesh	2601CS61
student-utkarsha	student	UTKARSHA RAVINDRA KAKULATE	2601CS62
student-navneet	student	NAVNEET KUMAR NITIN	2601CS63
student-noor	student	Noor Jamali	2601CS64
student-yellapu	student	Yellapu Akhila	2601CS65
student-perumalla	student	PERUMALLA ABHIJITH	2601CS66
student-ambati	student	AMBATI KEERTHI PRANAVI	2601CS67
student-debrup	student	Debrup Roy	2601CS68
student-srivally	student	SRIVALLY PERUMANDLA	2601CS69
student-anmol	student	Anmol Kumar Sah	2601CS70
student-dakarapu	student	DAKARAPU SAIJEETH	2601CS71
student-atishay	student	Atishay Jain	2601CS72
student-nihal-shoju	student	Nihal Shoju	2601CS73
student-utkarsh-raj-2	student	Utkarsh Raj	2601CS74
student-aman-kumar-2	student	Aman Kumar	2601CS75
student-devesh	student	Devesh Kumar	2601CS76
student-prerak	student	Prerak	2601CS77
student-shrishant	student	SHRISHANT KUMAR	2601CS78
student-tirth	student	Tirth Sorthiya	2601CS79
student-indukuri	student	Indukuri Kishore Reddy	2601CS80
student-mukiri	student	Mukiri Saatwik	2601CS81
student-umesh-saini	student	UMESH KUMAR SAINI	2601CS82
student-ashish-kumar	student	Ashish Kumar	2601CS83
student-krish	student	Krish	2601CS84
student-chaitanaya	student	Chaitanaya Nathalia	2601CS85
student-kanad	student	Kanad Laxman Kumavat	2601CS86
student-vaibhav-2	student	Vaibhav	2601CS87
student-ramavath	student	Ramavath Vinay	2601CS88
student-shaurya	student	Shaurya Gupta	2601CT01
student-arpit-raut	student	Arpit Ravikiran Raut	2601CT02
student-akshit	student	AKSHIT SHARMA	2601CT03
student-prince	student	Prince	2601CT04
student-aarya	student	Aarya Pankaj Patil	2601CT05
student-mandhani	student	Mandhani Netal Radheshyam	2601CT06
student-raj-gupta	student	Raj Gupta	2601CT07
student-amey	student	Amey Mittal	2601CT08
student-nitya	student	Nitya Bansal	2601CT09
student-manya	student	Manya Dhirawat	2601CT10
student-ananya-kumari	student	Ananya Kumari	2601CT11
student-prince-choudhary	student	Prince Choudhary	2601CT12
student-mane	student	MANE KANISHK RAJARAM	2601CT13
student-kashvi	student	Kashvi Verma	2601CT14
student-riyansh	student	Riyansh	2601CT15
student-archit-tulsyan	student	ARCHIT TULSYAN	2601CT16
student-mayank-jangid	student	Mayank Jangid	2601CT17
student-s-kavisan	student	S Kavisan	2601CT18
student-brijesh	student	Brijesh Nishad	2601CT19
student-rahul-singh	student	RAHUL SINGH	2601CT20
student-ritesh-kumar	student	Ritesh kumar	2601CT21
student-karan-kumar	student	Karan kumar	2601CT22
student-arnav-agrawal	student	Arnav Agrawal	2601CT23
student-devansh	student	Devansh Bansal	2601CT24
student-aman-kumar-3	student	Aman Kumar	2601CT25
student-harshit-sharma	student	HARSHIT CHANDRA SHARMA	2601CT26
student-peddabomma	student	Peddabomma Hari Hara Teja	2601CT27
student-madhav	student	madhav sharma	2601CT28
student-yukta	student	Yukta Singh	2601CT29
student-ashu	student	ASHU ANAND	2601CT30
student-dharavath	student	DHARAVATH DEEPANVITHA	2601CT31
student-tanav	student	Tanav	2601CT32
student-korra	student	Korra Arun	2601CT33
student-himesh	student	HIMESH GHOSLIYA	2601CT34
student-siddatapu	student	Siddatapu Ajay kumar	2601CT35
student-arnav-thakare	student	Arnav Thakare	2601CT36
student-fatima	student	Fatima Bint Kashif	2601EC01
student-girivardhan	student	Girivardhan A R	2601EC02
student-asif	student	Asif Uddaulah	2601EC03
student-srirup	student	Srirup Saha	2601EC04
student-mane-krishna	student	MANE SAI KRISHNA	2601EC05
student-shlok	student	Shlok Kumar	2601EC06
student-bondugula	student	BONDUGULA LIKITH SAI	2601EC07
student-lingam	student	Lingam Rohit	2601EC08
student-amula	student	AMULA SAHITHI	2601EC09
student-dev	student	Dev Pathak	2601EC10
student-harshit-singh	student	HARSHIT SINGH	2601EC11
student-valluri	student	VALLURI JEEVANAHARIKA	2601EC12
student-prince-sharma	student	Prince Sharma	2601EC13
student-garima	student	Garima	2601EC14
student-allu	student	ALLU SAI JAGAN	2601EC15
student-kashyap	student	KASHYAP CHANDRASHEKHAR BAGDE	2601EC16
student-natte	student	Natte Charan Sai Teja	2601EC17
student-kartikeya	student	Kartikeya Kumar Srivastava	2601EC18
student-vedansh	student	Vedansh Tandon	2601EC19
student-deepanshu	student	Deepanshu Jangir	2601EC20
student-pedada	student	PEDADA YUVA SAMAIKYA	2601EC21
student-aman-anand	student	Aman Anand	2601EC22
student-swarali	student	Swarali Sarang Bhola	2601EC23
student-jaybir	student	Jaybir Swami	2601EC24
student-shaik-akthar	student	shaik sohel akthar	2601EC25
student-yuvraj	student	Yuvraj Singh	2601EC26
student-srinaina	student	Srinaina Gowru	2601EC27
student-threenender	student	THREENENDER BHUKYA	2601EC28
student-anirudh	student	Anirudh G	2601EC29
student-damor	student	Damor Prant Narendrasinh	2601EC30
student-mallika	student	MALLIKA LOKESH	2601EC31
student-panthangi	student	Panthangi Abhishek	2601EC32
student-ramhungneile	student	Ramhungneile Nriame	2601EC33
student-mardala	student	MARDALA YOGI PRATHAP	2601EC34
student-taneti	student	TANETI VENKATA RAMA KANTH	2601EC35
student-suyash	student	SUYASH SRIVASTAVA	2601EC36
student-abhivadan	student	Abhivadan Srivastava	2601EC37
student-piyush	student	PIYUSH KUMAR	2601EC38
student-shubh	student	Shubh Laxmi	2601EC39
student-buyyala	student	Buyyala Rishitha	2601EC40
student-suyash-verma	student	Suyash Verma	2601EC41
student-gavva	student	Gavva Abhiram Reddy	2601EC42
student-krishna-sharma	student	Krishna Sharma	2601EC43
student-shivansh-kumar	student	Shivansh Kumar	2601EC44
student-shah	student	SHAH VRAJ KETUL	2601EC45
student-komal	student	KOMAL KUMARI	2601EC46
student-satya	student	Satya Kumar Shubham	2601EE01
student-mehul	student	MEHUL KUMAR	2601EE02
student-mankhush	student	Mankhush	2601EE03
student-bhagat	student	Bhagat Anushka Satyaprakash	2601EE04
student-purnim	student	Purnim Raj	2601EE05
student-shreyansh	student	Shreyansh Agarwal	2601EE06
student-ayush-narayan	student	Ayush Narayan	2601EE07
student-ayush-raj-2	student	Ayush Raj	2601EE08
student-pratyush-sharma	student	PRATYUSH SHARMA	2601EE09
student-brajendra	student	Brajendra Kumar	2601EE10
student-shashank	student	Shashank Vardhan	2601EE11
student-mukund	student	Mukund Madhav B	2601EE12
student-prajeeth	student	Prajeeth Batchu	2601EE13
student-rudra	student	Rudra Pratap Prajapat	2601EE14
student-sumit	student	Sumit Sarkar	2601EE15
student-alok	student	Alok Raj	2601EE16
student-sreeman	student	SREEMAN BURAM	2601EE17
student-subham	student	SUBHAM GHOSH	2601EE18
student-mandadi	student	MANDADI SIRIJA	2601EE19
student-anushree	student	Anushree Gupta	2601EE20
student-naitik	student	Naitik Gupta	2601EE21
student-raj-shekhar	student	Raj Shekhar	2601EE22
student-pratyusha	student	Pratyusha Maji	2601EE23
student-ambala	student	AMBALA ATHRIJ	2601EE24
student-gugulothu	student	Gugulothu Ram charan	2601EE25
student-samir	student	Samir Kumar	2601EE26
student-abhigyan	student	Abhigyan Singh	2601EE27
student-abhayanand	student	Abhayanand Kumar	2601EE28
student-ranveer-singh	student	Ranveer Singh	2601EE29
student-boda	student	BODA RAM CHARAN	2601EE30
student-harsh-sisodiya	student	Harsh Singh Sisodiya	2601EE31
student-paridhi	student	Paridhi Agrawal	2601EE32
student-ryan	student	Ryan Mathew	2601EE33
student-nandani	student	NANDANI GUPTA	2601EE34
student-ritisha	student	Ritisha Dutta	2601EE35
student-kokkalla	student	KOKKALLA SAI PAVAN TEJ	2601EE36
student-kodavath	student	KODAVATH HARSHAVARDHAN	2601EE37
student-jamalapurapu	student	JAMALAPURAPU SREE SAI DHARAHAAS	2601EE38
student-amit-kumar	student	AMIT KUMAR	2601EE39
student-bhosale	student	BHOSALE SAKSHAM SANJAYKUMAR	2601EE40
student-atul-rai	student	Atul Rai	2601EE41
student-kale	student	KALE SNEHA ZELAJI	2601EE42
student-keerthan	student	Keerthan B T	2601EE43
student-lakavath-anirvinya	student	Lakavath Anirvinya	2601EE44
student-prokash	student	Prokash Mondal	2601EE45
student-shaik-nousheer	student	SHAIK NOUSHEER	2601EE46
student-ashutosh	student	Ashutosh anand Shivjee Singh	2601ES01
student-rahul-shukla	student	Rahul Shukla	2601ES02
student-ashish-raj	student	Ashish Raj	2601ES03
student-parth-jaiswal	student	PARTH VIVEK JAISWAL	2601ES04
student-maloth	student	Maloth Parimala	2601ES05
student-gowtham	student	GOWTHAM A N	2601ES06
student-pranava	student	PRANAVA PRADHAN	2601ES07
student-rakshita	student	RAKSHITA JANU	2601ES08
student-arnav-wakode	student	Arnav Vijay Wakode	2601ES09
student-somnath	student	Somnath Majhi	2601ES10
student-yajat	student	Yajat Guliyani	2601ES11
student-mukul	student	Mukul Athwal	2601ES12
student-atharva	student	Atharva Manoj Deshmukh	2601ES13
student-didde	student	Didde Ramya	2601ES14
student-aman-thakur	student	Aman Kumar Thakur	2601ES15
student-charvi	student	Charvi Chandrashekhar Marathe	2601ES16
student-abhishek-singh	student	ABHISHEK V SINGH	2601ES17
student-dev-tiwari	student	Dev Tiwari	2601ES18
student-yadnya	student	Yadnya Namit Satam	2601ES19
student-jayshri	student	Jayshri Agarwal	2601ES20
student-jayansh	student	Jayansh Poonia	2601ES21
student-pradyuman	student	PRADYUMAN SINGH SHEKHAWAT	2601ES22
student-dhondi	student	DHONDI JUGGE PRATHEEK	2601ES23
student-verushka	student	Verushka Mamodia	2601MC01
student-harish	student	HARISH ATTRI	2601MC02
student-abhijeet-singh	student	ABHIJEET KUMAR SINGH	2601MC03
student-chandrachur	student	chandrachur mondal	2601MC04
student-lakshya	student	LAKSHYA MALKHEDE	2601MC05
student-saksham	student	SAKSHAM MITTAL	2601MC06
student-incharaa	student	Incharaa Shivaprakash	2601MC07
student-parth-sahu	student	PARTH SAHU	2601MC08
student-anubhu	student	Anubhu Das	2601MC09
student-mahesh	student	MAHESH HOTA	2601MC10
student-arkaprabho	student	Arkaprabho Sau	2601MC11
student-rehan	student	REHAN RIAZAHMAD MULLA	2601MC12
student-chirag	student	Chirag kumar	2601MC13
student-shreyasi	student	Shreyasi	2601MC14
student-devangana	student	Devangana Aneesh	2601MC15
student-satvik	student	Satvik Deorah	2601MC16
student-deepak-kumar	student	Deepak Kumar	2601MC17
student-abhishek-meena	student	Abhishek Meena	2601MC18
student-rachit	student	Rachit Shah	2601MC19
student-yash-sawsakade	student	Yash Purushottam Sawsakade	2601MC20
student-prateek	student	Prateek Daga	2601MC21
student-yogita	student	Yogita	2601MC22
student-murapaka	student	MURAPAKA CHANDRA SEKHAR	2601MC23
student-madhavaram	student	MADHAVARAM SAHARSH	2601MC24
student-nallapu	student	Nallapu Tanish	2601MC25
student-gaurav-maurya	student	Gaurav Singh Maurya	2601MC26
student-arshad	student	Arshad Umar Khan	2601MC27
student-tejas	student	Tejas Babhale	2601MC28
student-kumar	student	Kumar Naman	2601MC29
student-prince-saxena	student	Prince Saxena	2601MC30
student-satyam-2	student	SATYAM	2601MC31
student-varun	student	Varun	2601MC32
student-sourabh	student	Sourabh Kumar	2601MC33
student-rehan-ansari	student	Rehan Ansari	2601MC34
student-suragala	student	SURAGALA SATHWIK	2601MC35
student-geetika	student	Geetika Bhagat	2601MC36
student-banoth	student	Banoth Sidharth	2601MC37
student-ishan-mittal	student	ISHAN MITTAL	2601MC38
student-addala	student	Addala Suhani	2601MC39
student-yash-prasad	student	YASH PRASAD	2601MC40
student-aayush-paikaray	student	Aayush Paikaray	2601MC41
student-banavath	student	BANAVATH BHAVITHA	2601MC42
student-nityasha	student	Nityasha Rajput	2601MC43
student-mothukupally	student	Mothukupally Nihal Reddy	2601MC44
student-tadi	student	Tadi Bhargava Siva Durga	2601MC45
student-shivansh-gupta	student	Shivansh Kumar Gupta	2601MC46
student-md	student	Md Taha Hussain	2601MC47
student-ayush-kumar	student	Ayush Kumar	2601MC48
student-lovedev	student	Lovedev	2601MC49
student-lakshmi	student	Lakshmi Patni	2601MC50
student-donga	student	Donga Pal Sanjaybhai	2601ME01
student-kumar-shankar	student	KUMAR SHANKAR	2601ME02
student-mayuresh	student	Mayuresh Rajiv Nande	2601ME03
student-chinmay	student	Chinmay Aggarwal	2601ME04
student-priyanshi-goyal	student	Priyanshi Goyal	2601ME05
student-mohammad-ali	student	Mohammad Ali	2601ME06
student-aryan-2	student	aryan	2601ME07
student-shreyansh-ravi	student	Shreyansh Ravi	2601ME08
student-tatikonda	student	Tatikonda Karthik Reddy	2601ME09
student-pradyumna	student	Pradyumna Vasant Patil	2601ME10
student-satyam-singh	student	Satyam singh	2601ME11
student-gulshan	student	Gulshan kumar	2601ME12
student-ajay	student	AJAY KUMAR PANDIT	2601ME13
student-varanasi-rishin	student	VARANASI SAI RISHIN	2601ME14
student-aman-kumar-4	student	Aman Kumar	2601ME15
student-adrita	student	ADRITA BEJ	2601ME16
student-krishnam	student	Krishnam	2601ME17
student-jai	student	JAI JYOTHI SWAROOP	2601ME18
student-harshit-kumar-singh	student	HARSHIT KUMAR SINGH	2601ME19
student-puneet	student	Puneet Yadav	2601ME20
student-anurag-singh	student	Anurag Singh	2601ME21
student-gorle	student	GORLE GNANADEEP	2601ME22
student-dulapalli	student	DULAPALLI LEELA KRISHNA	2601ME23
student-hazare	student	HAZARE SANVI	2601ME24
student-maithreya	student	Maithreya Kompella	2601ME25
student-antharam	student	ANTHARAM KEERTHI PRIYA	2601ME26
student-dhruv-saxena	student	Dhruv Saxena	2601ME27
student-megavath	student	MEGAVATH SAINATH	2601ME28
student-navanitha	student	Navanitha J	2601ME29
student-mahika	student	Mahika Paliwal	2601ME30
student-aprajita	student	Aprajita Pandey	2601ME31
student-yashaswi	student	YASHASWI SUDHANV BALANAGU	2601ME32
student-gautam	student	GAUTAM KUMAR	2601ME33
student-singh	student	SINGH ARYAMAN HARENDRA	2601ME34
student-ashish-jacob	student	Ashish Jacob	2601ME35
student-aditya-maurya	student	Aditya Maurya	2601ME36
student-jajimogga	student	Jajimogga Teja	2601ME37
student-namala	student	NAMALA YESHWANTH KUMAR	2601ME38
student-kanishk	student	Kanishk Choudhary	2601ME39
student-aditya-kumar	student	Aditya Kumar	2601ME40
student-gedela	student	GEDELA BALA SAI GANESH	2601ME41
student-chhatrala	student	Chhatrala Shan Nishant	2601ME42
student-swapnil	student	Swapnil Chowdhury	2601ME43
student-s-vadavelli	student	S LITHESH CHETAN VADAVELLI	2601ME44
student-jai-bhatia	student	Jai Bhatia	2601ME45
student-krish-kumar	student	Krish Kumar	2601ME46
student-ishita-singh	student	ISHITA SINGH	2601ME47
student-dara	student	DARA VINOOTHNA	2601ME48
student-pranshu	student	Pranshu Agrawal	2601ME49
student-yusuf	student	Yusuf Imtiyaz	2601ME50
student-abhishek-k	student	Abhishek C K	2601ME51
student-kottisa-haripreeth	student	Kottisa Haripreeth	2601ME52
student-yelaka	student	YELAKA MIDHUN SAI	2601ME53
student-gun	student	Gun Agrawal	2601ME54
student-ratan	student	Ratan Kumar Yadav	2601ME55
student-muttamsetti	student	Muttamsetti Jayasri Durga	2601ME56
student-anurag-nath	student	Anurag Nath	2601ME57
student-rishabh-kumar	student	Rishabh kumar	2601ME58
student-poornima	student	POORNIMA TIWARI	2601ME59
student-rudra-mahlawat	student	RUDRA MAHLAWAT	2601ME60
student-shreya-kumari-2	student	Shreya Kumari	2601ME61
student-derin	student	Derin Kurian Jose	2601ME62
student-jiya	student	JIYA AGGARWAL	2601ME63
student-anaghmoy	student	Anaghmoy Chatterjee	2601ME64
student-jupudi	student	JUPUDI GOWTHAM	2601ME65
student-aadya	student	Aadya Singh	2601ME66
student-diya	student	Diya Agrawal	2601ME67
student-harshvardhan	student	Harshvardhan Kishor Shinde	2601ME68
student-anurag-nallani	student	Anurag Nallani	2601ME69
student-nishanth	student	Nishanth Reddy B R	2601ME70
student-shivjeet	student	SHIVJEET KUMAR	2601ME71
student-salunke	student	Salunke Swami Rahul	2601ME72
student-ramavath-naik	student	Ramavath Nithin Kumar Naik	2601ME73
student-bhukya-mohan	student	BHUKYA MOHAN	2601ME74
student-suman	student	Suman Mondal	2601ME75
student-rahul-raj	student	Rahul Raj	2601ME76
student-atharv	student	Atharv Joshi	2601ME77
student-murukuti	student	MURUKUTI SRIDHAR REDDY	2601ME78
student-bakuri	student	Bakuri Nava Deep Raju	2601ME79
student-gauransh	student	Gauransh Sharma	2601ME80
student-ritu	student	ritu kumari	2601ME81
student-parumandla	student	PARUMANDLA JASHWANTH	2601ME82
student-ayush-sanjay	student	Ayush Kumar Sanjay	2601MM01
student-vaishnavi	student	Vaishnavi L	2601MM02
student-aakash	student	AAKASH YADAV	2601MM03
student-anushka-ghosh	student	Anushka Ghosh	2601MM04
student-samaksh	student	Samaksh Vishnoi	2601MM05
student-dhanjit	student	Dhanjit Das	2601MM06
student-deepanshu-sharma	student	DEEPANSHU SHARMA	2601MM07
student-sumit-bisht	student	Sumit Singh Bisht	2601MM08
student-chintalwar	student	CHINTALWAR SANKALP MUKESH	2601MM09
student-apurva	student	Apurva Pranay	2601MM10
student-drishti	student	Drishti	2601MM11
student-ruhan	student	Ruhan Mazumder	2601MM12
student-kaushik	student	Kaushik Anand	2601MM13
student-metkar	student	METKAR PRANAV PARAG	2601MM14
student-abhishek-2	student	ABHISHEK	2601MM15
student-ganti	student	GANTI KOUSTHUBH	2601MM16
student-jayant	student	Jayant Raj	2601MM17
student-shivank-goyal	student	Shivank Goyal	2601MM18
student-harshawardhan	student	Harshawardhan Navnath Gaikwad	2601MM19
student-aryan-biswas	student	ARYAN BISWAS	2601MM20
student-samarth-bajpai	student	Samarth Bajpai	2601MM21
student-aditya-raj-2	student	Aditya Raj	2601MM22
student-arsia	student	ARSIA	2601MM23
student-aaranya	student	Aaranya Ganotra	2601MM24
student-shivam-krishnan	student	Shivam Krishnan	2601MM25
student-kuntamalla	student	KUNTAMALLA SUNIL SAI PHANINDER	2601MM26
student-aastha	student	Aastha Mevawala	2601MM27
student-adhyapak	student	ADHYAPAK SARTHAK JAY	2601MM28
student-subodh	student	SUBODH SHARMA	2601MM29
student-shyam	student	SHYAM SUNDAR GHORUI	2601MM30
student-rizwanur	student	Rizwanur Rahman	2601MM31
student-bhushan	student	Bhushan Vijay Barde	2601MM32
student-kirti	student	KIRTI VITTHAL FASATE	2601MM33
student-chintala	student	CHINTALA RISHITHA	2601MM34
student-wagmare	student	WAGMARE AJAY	2601MM35
student-gudala-bhanu	student	GUDALA VENKATA PRANAV BHANU	2601MM36
student-naitik-joshi	student	Naitik Joshi	2601MM37
student-rounak	student	Rounak Mandal	2601MM38
student-tamalika	student	TAMALIKA SAU	2601MM39
student-trisha	student	TRISHA SHARMA	2601MM40
student-chocha	student	Chocha Jaldeep palabhai	2601MM41
student-ayansh	student	Ayansh Pathak	2601MM42
student-m	student	M SIDDHARTH	2601MM43
student-ramavath-kumar	student	Ramavath Praveen Kumar	2601MM44
student-ankush	student	Ankush Mondal	2601PH01
student-amit-dhakad	student	Amit dhakad	2601PH02
student-ramavathula	student	RAMAVATHULA YATHEESWAR MANIKANTA NAIK	2601PH03
student-aarna	student	AARNA NITI PUSHKAR	2601PH04
student-rohan	student	ROHAN KUMAR SINGH	2601PH05
student-aanya-2	student	Aanya	2601PH06
student-shlok-tanmaya	student	Shlok Tanmaya	2601PH07
student-manas	student	MANAS VERMA	2601PH08
student-asish	student	Asish Behera	2601PH09
student-harsh-kumar	student	Harsh Kumar	2601PH10
student-saane	student	SAANE JYOTHSNA PRANATHI	2601PH11
student-vedika	student	VEDIKA MILIND JAMADAR	2601PH12
student-shaswat	student	SHASWAT GANGOPADHYAY	2601PH13
student-ujjwal	student	Ujjwal priyedarshi	2601PH14
student-aryan-chauhan	student	Aryan Singh Chauhan	2601PH15
student-aditya-garg	student	Aditya Garg	2601PH16
student-arnav-aryan	student	Arnav Aryan	2601PH17
student-nikhil-bharti	student	Nikhil Bharti	2601PH18
student-sushant	student	Sushant Jadhav	2601PH19
student-neha-2	student	NEHA	2601PH20
student-kore	student	KORE SHRIPAD RANGSIDHA	2601PH21
student-shreesh	student	Shreesh Srivastava	2601PH22
student-akhil	student	Akhil Saini	2601PH23
student-sivani	student	Sivani Anamika R	2601PH24
student-g	student	G E GURUKARTIK	2601PH25
student-yenuga	student	YENUGA PEDDIREDDY GARI KRISHNA	2601PH26
student-tisha	student	Tisha Ganvir	2601PH27
student-hritabrata	student	HRITABRATA SWARNAKAR	2601PH28
student-suraj	student	Suraj Singh	2601PH29
student-ponnakanti	student	PONNAKANTI VIVEK RIPUNJAY	2601PH30
student-banothu	student	Banothu Sai charan	2601PH31
student-patakota	student	PATAKOTA SUNAY KUMAR REDDY	2602CM01
student-pradyumn	student	Pradyumn Jha	2602CM02
student-lakshya-rajput	student	Lakshya Rajput	2602CM03
student-jaiveen	student	Jaiveen Kaur	2602CM04
student-ayansh-maurya	student	AYANSH UTKARSH MAURYA	2602CM05
student-arhan	student	Arhan Saha	2602CM06
student-ishant	student	Ishant	2602CM07
student-k-sanjeevani	student	K SANJEEVANI	2602CM08
student-k-nayak	student	K NAVEEN NAYAK	2602CM09
student-kakkerla	student	kakkerla pranay	2602CS01
student-bodapati	student	BODAPATI VEERA VENKATA RAVI	2602CS02
student-ram	student	Ram Prasannaa R	2602CS03
student-dev-asati	student	Dev Asati	2602CS05
student-somya	student	somya tikwani	2602CS06
student-muniza	student	MUNIZA PARVIN	2602CS07
student-anurag-kumar	student	Anurag Kumar	2602CS08
student-ankit-meena	student	ANKIT MEENA	2602CS09
student-spoorthy	student	Spoorthy M	2602CS10
student-rishu	student	Rishu Kumar	2602CS11
student-satyam-sinha	student	SATYAM SINHA	2602GT01
student-aayush-mishra	student	Aayush Mishra	2602GT02
student-aditya-kaushal	student	Aditya Kaushal	2602GT03
student-daidipya	student	DAIDIPYA DADHICH	2602GT04
student-yashraj	student	YASHRAJ JEPH	2602GT05
student-swati	student	Swati	2602GT06
student-rajesh	student	Rajesh	2602GT07
student-raunak	student	Raunak Patel	2602GT08
student-tushar	student	Tushar	2602MC01
student-mudit	student	Mudit Agrawal	2602MC02
student-abhishek-kumar-2	student	Abhishek Kumar	2602MC03
student-raikwar	student	Raikwar Shruti Vinod	2602MC04
student-polisetti	student	Polisetti Induja Sri Sivani	2602MC05
student-unhone	student	Unhone Pushpak Yogesh	2602MC06
student-potnuru-sartak	student	Potnuru Sartak	2602MC07
student-mohammad-bohra	student	MOHAMMAD BOHRA	2602MC08
student-v-kavin	student	V M KAVIN	2602MC09
student-pathlavath	student	Pathlavath Praveen Naik	2602MC10
student-rupesh	student	Rupesh	2602MT01
student-suhani-mehta	student	Suhani Mehta	2602MT02
student-aryan-khambayate	student	ARYAN RAJESH KHAMBAYATE	2602MT03
student-murthineni	student	MURTHINENI JAHNAVI NAIDU	2602MT04
student-pratyush-srivastav	student	Pratyush Srivastav	2602MT05
student-pratyush-srivastava	student	Pratyush Srivastava	2602MT06
student-vadthyavath-naveen	student	VADTHYAVATH NAVEEN	2602MT07
student-soumen	student	soumen pandit	2602MT08
student-saksham-singh	student	Saksham Singh	2602MT09
student-s-tharun	student	S K THARUN	2602MT10
student-r	student	R SYAM SUNDAR REDDY	2602PC01
student-mandalapu	student	Mandalapu Sai Sahasra	2602PC02
student-rohit-behera	student	ROHIT KUMAR BEHERA	2602PC03
student-kondaka	student	KONDAKA YASASWY	2602PC04
student-sahil	student	Sahil	2602PC05
student-jiya-chauhan	student	Jiya Ganeshsingh Chauhan	2602PC06
student-anumay	student	Anumay Gupta	2602PC07
student-ritesh-kumar-2	student	RITESH KUMAR	2602PC08
student-chinmay-kumar	student	Chinmay Kumar	2602ST01
student-saptarshi-patra	student	SAPTARSHI PATRA	2602ST02
student-natasha	student	Natasha Sen	2602ST03
student-subham-kumar	student	Subham kumar	2602ST04
student-anirudh-makkapati	student	Anirudh Makkapati	2602ST05
student-pranjal-chaudhari	student	Pranjal Narendra Chaudhari	2602ST06
student-shantanu-kumar	student	SHANTANU KUMAR	2602ST07
student-vanam	student	VANAM SAI SUDEEP	2602ST08
student-naitik-sharma	student	Naitik Sharma	2602ST09
student-kathir	student	Kathir Selvan G	2602VL01
student-vishnu	student	Vishnu Raj	2602VL02
student-aryan-singh	student	Aryan singh	2602VL03
student-andani	student	ANDANI VRAJ PINTUBHAI	2602VL04
student-y	student	Y S Vinisha Reddy	2602VL05
student-harshit-bajaj	student	Harshit Bajaj	2602VL06
student-neeraj	student	Neeraj Guguloth	2602VL07
student-dhande	student	DHANDE HEMANI VINOD	2602VL08
student-nagella	student	NAGELLA SHRIVATSA PRASAD	2603AI01
student-nishad	student	Nishad Baviskar	2603AI02
student-rahul-p	student	RAHUL PRASAD P	2603AI03
student-muskan	student	Muskan sharma	2603AI04
student-mohit-kumar	student	Mohit kumar	2603AI05
student-pratheeksha	student	PRATHEEKSHA B G	2603CB01
student-sriejan	student	Sriejan Das	2603CB02
student-bishu	student	Bishu Bhaskar	2603CB03
student-sachin-kumar	student	Sachin kumar	2603CB04
student-pulamolu	student	PULAMOLU JAGAN	2603CE01
student-vivek-singh	student	Vivek Kumar Singh	2603CE02
student-nikhil-singh	student	Nikhil Kumar Singh	2603CE03
student-bonuga	student	BONUGA KOUSHIK CHANDRA REDDY	2603CE04
student-akshadha	student	AKSHADHA RAMKUMAR	2603CE05
student-ayush-singh	student	Ayush Singh	2603CE06
student-alankrit	student	Alankrit Patel	2603CS01
student-champa	student	Champa Yeshey	2603CS02
student-kalpit	student	Kalpit Thakur	2603CS03
student-mithil	student	MITHIL MANISH PARCHURE	2603CT01
student-srimahi	student	Srimahi Reddy Yeltiwar	2603CT02
student-dipu	student	Dipu Kumar Kewat	2603CT03
student-kishan-bhava	student	Kishan Jothi Bhava	2603CT04
student-aditya-bhagat	student	ADITYA KUMAR BHAGAT	2603EC01
student-kaushik-kumar	student	Kaushik Kumar	2603EC02
student-jasmeet	student	JASMEET SINGH	2603EE01
student-arshita	student	Arshita Agarwal	2603EE02
student-lakshmi-paladugu	student	LAKSHMI REVANTH SAI PALADUGU	2603EE03
student-putluru	student	PUTLURU SAI VARSHITH REDDY	2603EE04
student-abhinav-anand	student	Abhinav Anand	2603EE05
student-ramchandra	student	Ramchandra Tholiya	2603ES01
student-thorat	student	THORAT DAKSH	2603ES02
student-pranil	student	PRANIL NIKHIL DUBE	2603ES03
student-rachit-agarwal	student	Rachit Agarwal	2603ES04
student-gurkeerat	student	GURKEERAT SINGH	2603MC01
student-barukunta	student	Barukunta Sankeerth	2603MC02
student-rashmita	student	Rashmita yadav	2603MC03
student-pranjal-nerkar	student	Pranjal Prashant Nerkar	2603ME01
student-karwar	student	KARWAR VEDANT DATTATRAY	2603ME02
student-poorvanjali	student	Poorvanjali	2603ME03
student-vikash	student	Vikash Vaibhav	2603ME04
student-sarda	student	Sarda Dhruv	2603ME05
student-mitadru	student	MITADRU KAR	2603ME06
student-biroju	student	BIROJU RUSHIKESH	2603ME07
student-rohit-choudhary	student	Rohit Choudhary	2603ME08
student-parikshit	student	Parikshit Bedi	2603ME09
student-moulik	student	Moulik Singh	2603ME10
student-donapati	student	Donapati Dhruva Kumar Reddy	2603ME11
student-nityasri	student	NITYASRI A	2603ME12
student-silimkar	student	Silimkar Tejas Mangesh	2603ME13
student-mayank-2	student	Mayank	2603MM01
student-ritojoy	student	Ritojoy Mandal	2603MM02
student-banavath-manoj	student	BANAVATH MANOJ	2603MM03
student-adya	student	Adya Agarwal	2603MM04
student-telugu	student	TELUGU SHASHANK	2603MM05
student-aryan-aggrawal	student	Aryan Aggrawal	2603PH01
student-arka	student	ARKA DAS	2603PH02
student-mahak-shakya	student	Mahak Shakya	2603PH03
\.


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (authentication_key);


--
-- Name: users users_roll_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_roll_number_key UNIQUE (roll_number);


--
-- PostgreSQL database dump complete
--

\unrestrict 70XtgJeSimh3yPjHcCvUg8Ty5ZdYpclukPDlSAPdQJoL8SWrygMWVmiP7QdQZXY


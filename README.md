# 🛒 E-Commerce Intelligence Platform

A production-grade web scraping & price monitoring system** built with Python, Scrapy, Selenium, PostgreSQL, Streamlit, and Docker.

Overview

This platform scrapes e-commerce product data at scale, tracks price changes over time, generates smart alerts, and visualises everything through an interactive analytics dashboard.

Built as a full-stack data engineering project demonstrating real-world skills across web scraping, database design, ETL pipelines, monitoring systems, and containerised deployment.

 Key Features

 Feature  Details 

Dual Scraping Engine                       Scrapy for static HTML, Selenium for JavaScript-rendered pages 

Price History Tracking                     Every price snapshot stored in PostgreSQL with full audit trail 

Smart Alert System                         Detects price drops/rises above configurable thresholds 

Anti-Detection                             Rotating user agents, request delays, exponential backoff retry 

Interactive Dashboard                      Streamlit, Plotly — Overview, Price Trends, Alerts, Scrape Runs 

Fully Containerised                        Docker Compose one-command deployment 

CI/CD Pipeline                             GitHub Actions for automated testing & scheduled scraping


Dashboard Pages


Overview : KPIs, product counts by category, stock availability 

Price Trends : Search products, view historical price charts 

Top Products : Best deals, highest rated, most reviewed 

Alerts : Price drop / rise / stock change notifications 

Scrape Runs : Full audit log of every spider run 


Ethical Scraping

This project is built with responsible scraping practices:

- Rate limiting — minimum 2-second delay between requests
- AutoThrottle — automatically slows down under server load
- Practice sites only — targets `books.toscrape.com` and `quotes.toscrape.com` (sites built for scraping education)
- No PII collection — only product/price data is collected


Tech Stack

Static Scraping : Scrapy 2.11 

Dynamic Scraping : Selenium 4, ChromeDriver 

Anti-Detection : Rotating User Agents, AutoThrottle 

Data Storage : PostgreSQL 15, SQLAlchemy ORM 

Monitoring : Custom price change detector 

Dashboard : Streamlit, Plotly 

Containerisation : Docker, Docker Compose 

CI/CD : GitHub Actions 

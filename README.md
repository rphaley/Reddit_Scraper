# Reddit_Scraper
This will scrape a given list of subreddits and parse out posts.  Provided a prompt, it will then utilize the OpenAI api to generate a response to the given post based on a preconfigured set of paramaters.  It will then email the user the original post along with the autogenerated response.

This deployment is currently for GCP and includes the following services:
*Cloud Functions
*Cloud Scheduler
*Cloud Storage
*Secret Manager


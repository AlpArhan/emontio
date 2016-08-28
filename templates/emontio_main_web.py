#!/usr/bin/python

import json
import pandas as pd
import numpy as np
import os
import argparse
import logging
import logging.handlers
from watson_developer_cloud import ToneAnalyzerV3, AlchemyDataNewsV1, AlchemyLanguageV1
from alchemyapi import AlchemyAPI
from os.path import join, dirname
import collections
import newspaper
from newspaper import Article, Source, Config
import requests
from flask import Flask
#import cf_deployment_tracker
import cgi
import sys
from datetime import datetime
import time
from collections import Counter
import re
import math
from pylab import array, arange, argsort, loglog, title, xlabel, ylabel, grid, logspace, log10,text,show
import matplotlib.pyplot as plt




# Object to scan files that contain news
class Emontio_Analyzer(object):
    """ Scans files to see which ones are relevant stock_id """


    def __init__(self, stock_id, stock_name, web_url):
        """ object """
        self.stock_id = stock_id
        self.stock_name = stock_name
        self.web_url = web_url

        self.targeted_paragraphs = []
        self.targeted_urls = []
        self.article_url = []
        self.article_title = []

        self.list_time_elapsed = []

        self.json_results = []
        self.url_title = []

        #**** Lists of results: ****
        self.result_scan_web = {}
        self.results_tone_analyzer = {}
        self.result_entity_extraction = []
        self.result_sentiment_analysis = {}

        #Excel Storage
        self.list_df_avg = []
        self.list_sentiment = []
        self.list_tone = []


    def get_api_key(self):

        # Open the key file and read the key
        print "--------------------------------"
        print "Retrieving API keys..."
        with open('credentials/watson_credentials.json', 'r') as f:
            self.watson_credentials = json.load(f)

        if not self.watson_credentials['username'] or not self.watson_credentials['password']:
            # The key file should't be blank
            print 'Error: valid username/password not found.'
            sys.exit(1)
        print "Watson Credentials are retrieved."

        with open('api_key.txt' , 'r') as f:
            api_key = f.readline().strip()

        os.system("python templates/alchemyapi.py %s" % api_key)

    def scan_targeted_web(self):

        print " -------------------------------"
        print "# SCANNING TARGETED WEBPAGE:"
        print " -------------------------------"

        print "Targeted Webpage: " , self.web_url

        startTime = datetime.now()
        targeted_webpage = newspaper.build(self.web_url, language = 'en', memoize_articles = False , fetch_images = False)

        # Targets an individual article.
        #targeted_article = Article(url = self.web_url, config)

        print "Number of articles in %s" % self.web_url ," = " , targeted_webpage.size()
        print "URLs: "

        self.result_scan_web["targeted_webpage"] = self.web_url;
        self.result_scan_web["article_count"] = targeted_webpage.size()

        list_word_frequency = []
        count = 0
        for article in targeted_webpage.articles:
            print article.url

            self.targeted_urls.append(article.url)

            print "Downloading the article:"
            article.download()

            try:
                print "Parsing the article paragraph from HTML..."
                article.parse()
            except Exception as e:
                print "Error ocurred while parsing HTML code: " + str(e)


            print "Extracting the paragraph..."
            paragraph = article.text

            print "Extraction is completed."

            word_frequency = Counter(paragraph.split())
            list_word_frequency.append(word_frequency[self.stock_name])
            print "Stock Name Count: " , word_frequency[self.stock_name]
            print "Ticker Symbol Count: " , word_frequency[self.stock_id]
            sum_word_frequency = sum(list_word_frequency)

            if (((self.stock_id + " ") in paragraph) or ((self.stock_name + " ") in paragraph)) and ("video" not in article.url):
                self.targeted_paragraphs.append(paragraph)
                self.article_url.append(article.url)
                self.article_title.append(article.title)

                print "SUCCESS: " , article.url

                successful_articles_json = {"url" : article.url, "title" : article.title  }

                self.json_results.append(successful_articles_json)

            count = count + 1

            print  "COUNT: " , count , " != " , targeted_webpage.size()

            if count == targeted_webpage.size():
                print count , " == " , targeted_webpage.size()
                print "Entire articles at the targeted webpage is read, downloaded, parsed and paragraphs are extracted."
                print "Time Elapsed: " , datetime.now() - startTime
                execution_time = datetime.now() - startTime
                self.list_time_elapsed.append(execution_time)

                break

            else:

                print "SCANNING..."

                continue

        try:
            print "Total Count of Stock Name in URLs: " , sum_word_frequency
        except Exception as e:
            print "Error ocurred during counting stock names in articles: " + str(e)

        #self.results_tone_analyzer["successful_articles"] = self.url_title#self.json_results

    def tf_idf(self):
        """ Normalize the frequency of stock name in the articles"""
        print "Initiating the word frequency test..."


        list_of_prepositions = [u'above', u'about', u'across', u'against',u'The', u'is',u'an',
                                u'along', u'among', u'around', u'at', u'before',
                                u'behind', u'below', u'beneath', u'beside', u'between',
                                u'beyond', u'by', u'during', u'except',
                                u'for', u'from',u'in', u'inside', u'into',u'like',u'near',u'of',
                                u'off', u'on',u'since',u'to', u'toward', u'through',u'under', u'until', u'up', u'upon',
                                u'with', u'within', u'the', u'a', u'and', u'for']


        try:
            #Zipf Distribution to assess threshold
            paragraphs = " ".join(self.targeted_paragraphs)
            words = paragraphs.split()
            frequency = Counter(x for x in words if x not in list_of_prepositions)
            counts = array(frequency.values())
            tokens = frequency.keys()

            ranks = arange(1, len(counts)+1)
            indices = argsort(-counts)
            frequencies = counts[indices]
            loglog(ranks, frequencies, marker=".")
            title("Zipf plot for Combined Article Paragraphs")
            xlabel("Frequency Rank of Token")
            ylabel("Absolute Frequency of Token")
            grid(True)
            for n in list(logspace(-0.5, log10(len(counts)-1), 20).astype(int)):
                dummy = text(ranks[n], frequencies[n], " " + tokens[indices[n]],
                verticalalignment="bottom",
                horizontalalignment="left")
            #plt.plot(np.unique(ranks), np.poly1d(np.polyfit(ranks, frequencies, 10))(np.unique(ranks)))
            slope=np.polyfit(ranks, frequencies, 0)
            for value in slope:
                print value
                zipf_threshold = value
            ## NEED TO ADD- FITTED LINE. Due to an error in the value of threshold its currently not in-use while paragraph extraction.##
        except Exception as e:
            print "Error occurred during Zipf Distribution: " + str(e)



        #Inverse-document Frequency
        document_size = self.result_scan_web["article_count"]
        document_success = len(self.article_url)
        try:
            idf = math.log(float(document_size)/float(document_success))
        except Exception as e:
            print "No Successful Articles in this webpage: " + str(e)

        #Term Frequency
        list_total_count = []
        for paragraph in self.targeted_paragraphs:
            words = paragraph.split()
            word_frequency = Counter(x for x in words if x not in list_of_prepositions)
            stock_frequency = word_frequency[self.stock_name]
            list_total_count.append(stock_frequency)

        total_count = sum(list_total_count)
        print "TOTAL WORD COUNT:" , total_count

        print "COUNT BEFORE:"
        print "urls = " , len(self.article_url)

        list_fail_values = []
        for paragraph in self.targeted_paragraphs:
            words = paragraph.split()
            word_frequency = Counter(x for x in words if x not in list_of_prepositions)
            stock_frequency = word_frequency[self.stock_name]
            ticker_symbol_frequency = word_frequency[self.stock_id]
            print "TERM FREQUENCY: ", stock_frequency
            print "DIVISION: " , (float(stock_frequency)/float(total_count))
            try:
                tf_idf_weight = (float(stock_frequency)/float(total_count)) * float(idf)
            except Exception as e:
                print "Error ocurred during division. total_count is zero, meaning no successful articles: " + str(e)
            print "TF-IDF-WEIGHT = " , tf_idf_weight
            if tf_idf_weight <= 0.30: # Gives the articles that lie within the 30th percentile of success.
                index = self.targeted_paragraphs.index(paragraph)
                self.targeted_paragraphs.remove(paragraph)

                url_value = self.article_url[index]
                title_value = self.article_title[index]
                fail_dict = {'url': url_value , 'title' : title_value}
                list_fail_values.append(fail_dict)

                print "IRRELEVANT ARTICLE DETECTED..."
                print "DELETING " , url_value
                del self.article_url[index]
                del self.article_title[index]

            else:
                pass

        print "COUNT AFTER: "
        print "urls = " , len(self.article_url)


        print "FAILED ARTICLES: "
        print "# "  , len(list_fail_values)
        print "articles:" , list_fail_values

        #titles_in_fail = {d['title'] for d in list_fail_values if 'title' in d}
        #self.json_results[:] = [d for d in self.json_results if d.get('title') not in titles_in_fail]

        self.json_results[:] = [i for i in self.json_results if i not in list_fail_values]
        self.results_tone_analyzer["successful_articles"] = self.json_results

        print " ----------------------------"
        print "Number of Successful Articles = " , len(self.article_url)
        print "SUCCESSFUL URLs: " ,
        for article in self.article_url:
            print article
        print " ----------------------------"


    def Tone_Reader(self):

        print " ----------------------------"
        print "# STARTING TONE ANALYZER:"
        print " ----------------------------"

        startTime = datetime.now()
        data_frames = []
        data_frame_storage = []
        count = 0
        for paragraph in self.targeted_paragraphs :
            print "Reading the extracted articles..."
            if (self.stock_id in paragraph) or (self.stock_name in paragraph) or (self.stock_name.lower() in article.url):

                # Starting IBM WATSON Tone Analyzer Service. Makes an API call for each successful filename.
                tone_analyzer = ToneAnalyzerV3(
                    username= self.watson_credentials['username'] ,
                    password= self.watson_credentials['password'],
                    version='2016-02-11')
                print "Tone Analyzer is initiated."

                # DOCUMENT TONE: Extracts columns to prepare numbers
                results = tone_analyzer.tone(text=paragraph)

                emotion_tone = results["document_tone"]["tone_categories"][0]["tones"]
                writing_tone = results["document_tone"]["tone_categories"][1]["tones"]
                social_tone = results["document_tone"]["tone_categories"][2]["tones"]

                # DOCUMENT TONE: Prepares the dataframe for each tone category.
                print "Preparing results..."
                df_emotion_tone = pd.DataFrame(emotion_tone)
                df_writing_tone = pd.DataFrame(writing_tone)
                df_social_tone = pd.DataFrame(social_tone)



                # DOCUMENT TONE:  Analyzes the tone score for emotion, writing, and social.
                # emotion_tone
                less_emotion = df_emotion_tone.loc[df_emotion_tone.score <= 0.5] # Less likely to be perceived.
                high_emotion = df_emotion_tone.loc[df_emotion_tone.score >= 0.75] # High likely to be perceived.

                # writing_tone
                less_writing = df_writing_tone.loc[df_writing_tone.score <= 0.25] # Less likely to be perceived.
                high_writing = df_writing_tone.loc[df_writing_tone.score >= 0.75] # High likely to be perceived.

                # social_tone
                less_social = df_social_tone.loc[df_social_tone.score <= 0.25] # Less likely to be perceived.
                high_social = df_social_tone.loc[df_social_tone.score >= 0.75] # High likely to be perceived.



                # DataFrame High likely
                high_likely_frame = pd.concat([high_emotion, high_writing, high_social])

                # DataFrame Less Likely
                less_likely_frame = pd.concat([less_emotion, less_writing, less_social])


                # Combines the dataframes for all categories.
                df_combine = pd.concat([df_emotion_tone , df_writing_tone]) # -> adds side by side.
                full_df = pd.concat([df_combine , df_social_tone])

                print "DOCUMENT-LEVEL RESULTS:  "

                print "ARTICLE TITLE: " , self.article_title[count]
                print 'ARTICLE URL: ' , self.article_url[count]
                print "DATA FRAME: "

                full_df = full_df.reset_index()
                del full_df['index']
                print full_df

                data_frames.append(full_df)
                df_analysis = pd.concat(data_frames)

                df_tone_storage = full_df
                df_tone_storage.insert(loc=3,column="article_title",value=self.article_title[count])
                data_frame_storage.append(df_tone_storage)
                data_frame_tone_concat = pd.concat(data_frame_storage)

                self.list_tone.append(data_frame_tone_concat)
                count = count + 1

                print "----------- Tone Analysis is completed. ---------------"

            else:
                print "Scanned articles are irrelevant."



        try:

            print "AVERAGE VALUES FOR TONE ANALYZER DATA FRAME:"
            # Takes an average of the combined results.

            data_average = {'anger_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'anger', 'score'].mean()],
            'disgust_avg' :  [df_analysis.loc[df_analysis['tone_id'] == 'disgust', 'score'].mean()],
            'fear_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'fear', 'score'].mean()],
            'joy_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'joy', 'score'].mean()],
            'sadness_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'sadness', 'score'].mean()],
            'analytical_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'analytical', 'score'].mean()],
            'confident_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'confident', 'score'].mean()],
            'tentative_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'tentative', 'score'].mean()],
            'openness_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'openness_big5', 'score'].mean()],
            'conscientiousness_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'conscientiousness_big5', 'score'].mean()],
            'extraversion_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'extraversion_big5', 'score'].mean()],
            'agreeableness_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'agreeableness_big5', 'score'].mean()],
            'neuroticism_big5_avg' : [df_analysis.loc[df_analysis['tone_id'] == 'neuroticism_big5', 'score'].mean()]}

            df_avg = pd.DataFrame(data = data_average).T
            self.list_df_avg.append(df_avg)
            result = {}
            for k,v in data_average.iteritems():
                result[k] = v[0]

            self.results_tone_analyzer["average_tone_results"] = result
            #print df_avg.to_sql(name='tone_average', index=False, con=self.db, if_exists='append')
            #print "END RESULT: " + str(self.results_tone_analyzer)

        except Exception as e:
            print "Error during tone analysis: " + str(e)

        print self.results_tone_analyzer
        print "Time Elapsed: " , datetime.now() - startTime
        execution_time = datetime.now() - startTime
        self.list_time_elapsed.append(execution_time)

    def Entity_Extraction(self):

        print " ----------------------------"
        print "# STARTING ENTITY EXTRACTION:"
        print " ----------------------------"

        count = 0

        os.system("python templates/alchemyapi.py 32449e7b4f6b65f9ef5cfd84b7128a46440a9402")

        startTime = datetime.now()
        # Create the AlchemyAPI Object
        alchemyapi = AlchemyAPI()
        for paragraph in self.targeted_paragraphs:
            response = alchemyapi.entities('text', paragraph, {'sentiment': 1})

            if response['status'] == 'OK':

                print "DOCUMENT-LEVEL RESULTS:  "

                print "ARTICLE TITLE: " , self.article_title[len(self.article_title) - len(self.article_title) + count]
                print 'ARTICLE URL: ' , self.article_url[len(self.article_url) - len(self.article_url) + count]
                print "DATA FRAME: "
                count = count + 1

                for entity in response['entities']:

                    entity_text = entity['text']
                    entity_type = entity['type']
                    entity_relevance = entity['relevance']
                    entity_sentiment_type = entity['sentiment']['type']

                    if 'score' in entity['sentiment']:
                        entity_sentiment_score = entity['sentiment']['score']

                    df_entity_extraction = pd.DataFrame(data = {'text': [entity_text],
                                                         'type': [entity_type],
                                                         'relevance': [entity_relevance],
                                                         'sentiment': [entity_sentiment_type],
                                                         'sentiment_score': [entity_sentiment_score]})

                    print "***** ENTITY EXTRACTION RESULTS: *****"
                    print df_entity_extraction.T
                    df_transpose = df_entity_extraction.T


                    entity_json_results = df_transpose.to_dict() #######
                    self.result_entity_extraction.append(entity_json_results)

                else:
                    pass

            else:
                print 'Error in entity extraction call: ', response['statusInfo']

        print "----------- Entity Extraction is completed. ---------------"

        print "Time Elapsed: " , datetime.now() - startTime
        execution_time = datetime.now() - startTime
        self.list_time_elapsed.append(execution_time)


    def Sentiment_Analysis(self):

        print " ----------------------------"
        print "# STARTING SENTIMENT ANALYSIS:"
        print " ----------------------------"

        df_sentiment_combined = []
        list_data_sentiment = []
        startTime = datetime.now()
        count = 0
        # Create the AlchemyAPI Object
        alchemyapi = AlchemyAPI()
        for paragraph in self.targeted_paragraphs:
            response = alchemyapi.sentiment('text', paragraph)
            if response['status'] == 'OK':

                print '---------------------------------------'
                print "***** DOCUMENT SENTIMENT RESULTS: *****"
                print "DOCUMENT-LEVEL RESULTS:  "

                print "ARTICLE TITLE: " , self.article_title[count]
                print 'ARTICLE URL: ' , self.article_url[count]
                print "DATA FRAME: "

                try:
                    data_sentiment_formatted = {'article_title' : self.article_title[count],
                                      'type': response['docSentiment']['type'],
                                      'score': response['docSentiment']['score']}
                except:
                    pass

                data_sentiment = {'article_title' : self.article_title[count],
                                  'type': [response['docSentiment']['type']],
                                  'score': [response['docSentiment']['score']]}
                count = count + 1

                list_data_sentiment.append(data_sentiment_formatted)
                df_sentiment_analysis = pd.DataFrame(data = data_sentiment).T
                print df_sentiment_analysis

                sentiment_json_results= df_sentiment_analysis.to_dict() ########
                df_sentiment_combined.append(df_sentiment_analysis)

            else:
                print('Error in sentiment analysis call: ', response['statusInfo'])


        self.result_sentiment_analysis["sentiment_analysis_result"] = list_data_sentiment


        try:
            print "***** AVERAGE DOCUMENT SENTIMENT RESULTS: *****"
            df_sentiment_avg = pd.concat(df_sentiment_combined).T
            self.list_sentiment.append(df_sentiment_avg)
            sentiment_avg_json_results = df_sentiment_avg.to_dict() ##########

        except Exception as e:
            print "Error during average sentiment analysis calculation." + str(e)

        try:
            sentiment_score = np.array(df_sentiment_avg)
            sentiment_score_even = sentiment_score[:, 0::2]
            sentiment_score_calculation = [float(i) for i in sentiment_score_even[0]]
            avg_sentiment_score = sum(sentiment_score_calculation)/len(sentiment_score_calculation)
            print "AVERAGE SENTIMENT SCORE = " , avg_sentiment_score


            average_sentiment_score = { "average_sentiment_score" :  avg_sentiment_score}
            df_sentiment_average = pd.DataFrame(average_sentiment_score)
            self.list_sentiment.append(df_sentiment_average)
            self.result_sentiment_analysis["average_sentiment_score"] = average_sentiment_score

        except:
            pass


        print "----------- Sentiment Analysis is completed. ---------------"

        print "Time Elapsed: " , datetime.now() - startTime
        execution_time = datetime.now() - startTime
        self.list_time_elapsed.append(execution_time)

        print self.result_sentiment_analysis

    def excel_storage(self):

        print "Excel storage of data begins..."
        # Add excel storage
        start = "http://www."
        end = ".com"
        print type(self.web_url)
        try:
            web_name = re.search('%s(.*)%s' % (start, end), self.web_url).group(1)
        except AttributeError :
            web_name = re.search('%s(.*)%s' % (start, end), self.web_url)
        date_today = datetime.now().strftime("%Y%m%d")
        try:
            current_directory = os.path.dirname(os.path.abspath('__file__'))
            data_storage_path = current_directory +"/data_storage"
            if not os.path.exists(data_storage_path):
                os.mkdir(data_storage_path)
        except Exception as e:
            print "Error ocurred during accessing a path: " + str(e)
        if not os.path.exists(data_storage_path + "/" + self.stock_name):
            os.mkdir(data_storage_path + "/" + self.stock_name)

        if not os.path.exists(data_storage_path + "/" + self.stock_name + "/" + web_name):
            os.mkdir(data_storage_path + "/" + self.stock_name + "/" + web_name)

        try:
            print "Storing Average Tone Analysis results.."
            for frame in self.list_df_avg:
                frame.to_csv(data_storage_path + "/" + str(self.stock_name) + "/" + web_name + "/" + "tone_average" + "_" + date_today +".csv")
            print "Storing tone results..."
            for frame in self.list_tone:
                frame.to_csv(data_storage_path + "/" + str(self.stock_name) + "/" + web_name + "/" + "tone_results" + "_" + date_today +".csv" , encoding='utf-8')
            print "Storing Sentiment Analysis results.."
            for frame in self.list_sentiment:
                frame.to_csv(data_storage_path + "/" + str(self.stock_name) + "/" + web_name + "/" + "sentiment_results" + "_" + date_today +".csv", encoding='utf-8')
            print "Data storage is completed."
        except Exception as e:
            print "Error during data storage: " + str(e)


def handle_form_submit(stock_id, stock_name, web_url):

    print 'emontio: handle_form_submit'

    analyzer = Emontio_Analyzer(stock_id, stock_name, web_url)
    analyzer.get_api_key()
    analyzer.scan_targeted_web()
    analyzer.tf_idf()
    analyzer.Tone_Reader()
    #analyzer.Entity_Extraction()
    analyzer.Sentiment_Analysis()
    analyzer.excel_storage()

    return analyzer


def main():

    print 'emontio: running as executable'
    analyzer = Emontio_Analyzer(stock_id, stock_name, web_url)
    analyzer.get_api_key()
    analyzer.scan_targeted_web()
    analyzer.Tone_Reader()
    analyzer.Entity_Extraction()
    analyzer.Sentiment_Analysis()
    #analyzer.clean_up();

    #complete_results = sys.stdout


if __name__ == '__main__':
    print '@@@@@@@' + str(sys.argv)
    main()

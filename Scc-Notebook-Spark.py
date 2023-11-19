# Databricks notebook source
# obtain all rentals from cosmos bd rentals container

from pyspark.sql.functions import *


try:

    readConfigHouses = {
        "spark.cosmos.accountEndpoint": "https://scc2324-60677.documents.azure.com:443/",
        "spark.cosmos.accountKey": "GhtDrRilEAgs3ysAvFvRpbHu6KEAvaijt1qEot2MLQjyyt6cLMWTRZCgsanDOKfOdfjrTNXamxBMACDb0qGy5Q==",
        "spark.cosmos.database": "scc2324-60677",
        "spark.cosmos.container": "houses",
        "spark.cosmos.read.customQuery": 
        "SELECT h.id, h.name, h.location, h.description, h.photosIds, h.ownerName, h.normalPrice, h.promotionPrice, h.promotionIntervals FROM houses h"

    }

    readConfigRentals = {
        "spark.cosmos.accountEndpoint": "https://scc2324-60677.documents.azure.com:443/",
        "spark.cosmos.accountKey": "GhtDrRilEAgs3ysAvFvRpbHu6KEAvaijt1qEot2MLQjyyt6cLMWTRZCgsanDOKfOdfjrTNXamxBMACDb0qGy5Q==",
        "spark.cosmos.database": "scc2324-60677",
        "spark.cosmos.container": "rentals",
        "spark.cosmos.read.customQuery": "SELECT r.id, r.houseId, r.user,r.startDate,r.endDate,r.locationOfTheHouse, r._ts FROM rentals r WHERE r.isImaginary = false"

    }

    houses = spark.read.format("cosmos.oltp").options(**readConfigHouses) \
        .option("spark.cosmos.read.inferSchema.enabled", "true") \
            .load()

    houses = houses.withColumnRenamed("id", "houseId")

    rentals = spark.read.format("cosmos.oltp").options(**readConfigRentals) \
        .option("spark.cosmos.read.inferSchema.enabled", "true") \
            .load()

    rentals = rentals.withColumnRenamed("id", "rentalId").withColumnRenamed("houseId", "r_houseId")

    rentals.createOrReplaceTempView("rentals")


    #-------------------------------------
    # caculate best Promotion score


    bestPromotions = houses.select("houseId","normalPrice","promotionPrice")
    bestPromotions = bestPromotions.withColumn("dif", col("promotionPrice") - col("normalPrice"))
    bestPromotions = bestPromotions.drop("promotionPrice","normalPrice")

    min_value = bestPromotions.agg(min("dif")).first()[0]
    max_value = bestPromotions.agg(max("dif")).first()[0]

    bestPromotions = bestPromotions.withColumn("score_1", (col("dif") - min_value) / (max_value - min_value))
    bestPromotions = bestPromotions.drop("dif")


    # ------------------------------------

    # ------------------------------------
    #calculate trending houses score


    trendingHouses = spark.sql("""SELECT rentals.r_houseId, count(*) AS rentalCount FROM rentals GROUP BY rentals.r_houseId""")

    min_value = trendingHouses.agg(min("rentalCount")).first()[0]
    max_value = trendingHouses.agg(max("rentalCount")).first()[0]

    trendingHouses = trendingHouses.withColumn("score_2", (col("rentalCount") - min_value) / (max_value - min_value))
    trendingHouses = trendingHouses.drop("rentalCount")



    # ----------------------------------

    # ----------------------------------
 
    # calculate locations score

    trendinglLocations = spark.sql("""SELECT rentals.locationOfTheHouse, count(*) AS locationCount FROM rentals GROUP BY rentals.locationOfTheHouse""")

    min_value = trendinglLocations.agg(min("locationCount")).first()[0]
    max_value = trendinglLocations.agg(max("locationCount")).first()[0]

    trendinglLocations = trendinglLocations.withColumn("score_3", (col("locationCount") - min_value) / (max_value - min_value))
    trendinglLocations = trendinglLocations.drop("locationCount")



    # ----------------------------------

    # ----------------------------------

    #join all

    suggestions = houses.join(trendingHouses, trendingHouses.r_houseId == houses.houseId)
    suggestions = suggestions.drop("r_houseId")


    suggestions = suggestions.join(trendinglLocations, trendinglLocations.locationOfTheHouse == suggestions.location)
    suggestions = suggestions.drop("locationOfTheHouse")


    bestPromotions = bestPromotions.withColumnRenamed("houseId","houseId_1")
    suggestions = suggestions.join(bestPromotions, bestPromotions.houseId_1 == suggestions.houseId)
    suggestions = suggestions.drop("houseId_1")



    suggestions = suggestions.withColumn("score", col("score_1") + col("score_2") + col("score_3"))
    suggestions = suggestions.drop("score_1","score_2","score_3")
    
    suggestions = suggestions.orderBy(desc("score"))
    suggestions = suggestions.withColumnRenamed("houseId","id")

    display(suggestions)


    writeConfig = {
        "spark.cosmos.accountEndpoint": "https://scc2324-60677.documents.azure.com:443/",
        "spark.cosmos.accountKey": "GhtDrRilEAgs3ysAvFvRpbHu6KEAvaijt1qEot2MLQjyyt6cLMWTRZCgsanDOKfOdfjrTNXamxBMACDb0qGy5Q==",
        "spark.cosmos.database": "scc2324-60677",
        "spark.cosmos.container": "spark"
    }
    suggestions.write.format("cosmos.oltp").options(**writeConfig) \
        .mode("append") \
            .save()













except Exception as e:
    print(e)

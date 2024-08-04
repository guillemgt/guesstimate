import * as cheerio from 'cheerio';
import {encode, decode} from 'gpt-3-encoder'
import { config } from 'dotenv';
import path from 'path';
config();

import fs from 'fs';


/* =============================
    Calling APIs
   ============================= */

import { areDisambiguation, normalizeArticles } from "./general/wikipedia.js"
import { removeDuplicates, parallelCalls } from "./general/utils.js"

/* =============================
    Main
   ============================= */

async function main(params = {
    input_path: "topics.json",
    output_path: "data/topics.json"
}) {
    let topics_file = params.input_path;
    let output_path = params.output_path;

    let topics = JSON.parse(fs.readFileSync(topics_file, 'utf8'));
    topics = await removeDuplicates(topics);

    let chunked_topics = [];
    for(let i=0; i<topics.length; i+=50){
        chunked_topics.push(topics.slice(i, i+50));
    }

    // Check if there are articles that need disambiguation

    try {
        const results = await parallelCalls(areDisambiguation, chunked_topics, 10);

        let some_dis = false;
        for(let result of results){
            for(let dis of result){
                console.log("Disambiguation needed for", dis);
                some_dis = true;
            }
        }
        if(some_dis) process.exit(0);

    } catch (error) {
        console.error('Error:', error);
        process.exit(0);
    }
    
    // Normalize article titles

    let normalized_topics = [];
    try {
        const results = await parallelCalls(normalizeArticles, chunked_topics, 10);
        for(let result of results){
            normalized_topics = normalized_topics.concat(result);
        }
    } catch (error) {
        console.error('Error:', error);
        process.exit(0);
    }

    // Save new topics.json to joinPath(data_path, output_file)
    normalized_topics = await removeDuplicates(normalized_topics);
    fs.writeFileSync(output_path, JSON.stringify(normalized_topics));
}

export { main };

// GPT-4o mini: $0.4779 for 6006 questions in 547 topics
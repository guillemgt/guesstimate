import * as cheerio from 'cheerio';
import {encode} from 'gpt-3-encoder'
import path from 'path';

import fs from 'fs';

/* =============================
    Calling APIs
   ============================= */

import { query } from "./general/wikipedia.js"
import { removeDuplicates, parallelCalls } from "./general/utils.js"

/* =============================
    Main
   ============================= */

async function query_and_process_wiki_article(topic_and_path){
    let [topic, wikidump_path] = topic_and_path;
    let response = await query(topic);
    await process_wiki_article(response, topic, wikidump_path);
}

async function process_wiki_article(wikipedia_response_json_text, topic, wikidump_path){
    console.log("Processing article", topic);

    if(fs.existsSync(wikidump_path)){
        return;
    }
            
    let json = JSON.parse(wikipedia_response_json_text)
    if(json.parse == undefined){
        console.log("Article not found");
        return;
    }
    let html_txt = json.parse.text["*"]

    const $ = cheerio.load(html_txt)
    $("sup.reference").remove()
    $("style").remove()
    $("script").remove()

    let parsed_text = ""
    let next_parsed_text = ""
    let last_dots = false

    let ps = $(".mw-parser-output > p")
    for(let i=0; i<ps.length; i++){

        const paragraphElement = $(ps[i])

        // Get the HTML content of the selected element
        const originalHtml = paragraphElement.html();

        // Replace <sup> and <sub> tags with desired notations
        const modifiedHtml = originalHtml.replace(/<sup>(.*?)<\/sup>/g, '^($1)').replace(/<sub>(.*?)<\/sub>/g, '_($1)');

        // Update the content of the selected DOM element with the modified HTML
        paragraphElement.html(modifiedHtml);


        let text = paragraphElement.text()
        let has_number = /\d/.test(text)
        if(has_number){
            next_parsed_text =  parsed_text + paragraphElement.text()
            last_dots = false
        }else{
            if(!last_dots){
                next_parsed_text = parsed_text + "[...]\n"
                last_dots = true
            }
        }
        
        const encoded = encode(next_parsed_text)
        if(encoded.length > 9000)
            break
        parsed_text = next_parsed_text
    }

    parsed_text = parsed_text.trim();
    if(parsed_text.length == 0 || parsed_text == '[...]')
        return;

    fs.writeFileSync(wikidump_path, parsed_text);
}


async function main(params = {
    "input_path": "topics.json",
    "output_path": "wikipedia_dumps/",
}) {
    let topics_file = params.input_path;
    let dir_wikidump = params.output_path;
    fs.mkdirSync(dir_wikidump, { recursive: true });

    let topics = JSON.parse(fs.readFileSync(topics_file, 'utf8'));
    topics = await removeDuplicates(topics);

    for(let i=0; i<topics.length; i++){
        topics[i] = [topics[i], path.join(dir_wikidump, topics[i] + ".txt")];
    }

    try {      
        await parallelCalls(query_and_process_wiki_article, topics, 5);
    } catch (error) {
        console.error('Error:', error);
        process.exit(0);
    }
}

export { main };

// GPT-4o mini: $0.4779 for 6006 questions in 547 topics
import path from 'path';
import {encode, decode} from 'gpt-3-encoder'
import { remove as remove_ambiguous_unicode } from 'confusables';

import fs from 'fs';

/* =============================
    Main
   ============================= */

const count_tokens = (encoded) => {
    let tokens = {};
    for(let token of encoded){
        if(tokens[token] == undefined){
            tokens[token] = 1;
        }else{
            tokens[token]++;
        }
    }
    return tokens;
}

const count_overlap = (tokens1, tokens2) => {
    let count = 0;
    for(let i=0; i<Object.keys(tokens1).length; i++){
        let key = Object.keys(tokens1)[i];
        if(tokens2[key] == undefined) continue;
        count += Math.min(tokens1[key], tokens2[key]);
    }
    return count;
}

function _is_period(string, index){
    // If not a dot, return false
    if(string[index] != "."){
        return false;
    }

    // Check if it is part of a number
    if(index > 0 && index < string.length-1){
        if(string[index-1].match(/[0-9]/) && string[index+1].match(/[0-9]/)){
            return false;
        }
    }

    return true;
}

async function find_excerpt_in_topic(topic, questions, wikidump_path){
    console.log("Processing topic", topic);

    const wiki_text = remove_ambiguous_unicode(fs.readFileSync(wikidump_path, 'utf8'));
    const wiki_encoded = encode(wiki_text);

    for(let question of questions){
        const reported_excerpt = remove_ambiguous_unicode(question["reported_excerpt"]);
        const excerpt_encoded = encode(reported_excerpt);
        let excerpt_tokens = count_tokens(excerpt_encoded);

        let best_i = 0;
        let best_overlap = 0;
        for(let i=0; i<wiki_encoded.length-excerpt_encoded.length; i++){
            let wiki_tokens = count_tokens(wiki_encoded.slice(i, i+excerpt_encoded.length));
            let unordered_overlap = count_overlap(excerpt_tokens, wiki_tokens);
            if(unordered_overlap > best_overlap){
                best_overlap = unordered_overlap;
                best_i = i;
            }
        }

        let start_i = decode(wiki_encoded.slice(0, best_i)).length;
        let end_i = start_i + decode(wiki_encoded.slice(best_i, best_i+excerpt_encoded.length)).length;

        let d = 0;
        for(; start_i>=0 && !_is_period(wiki_text, start_i); start_i--, d++);
        if(wiki_text.slice(start_i-3, start_i+2) == "[...]"){
            start_i += 2;
        }else if(d < 8){
            start_i--;
            for(; start_i>=0 && !_is_period(wiki_text, start_i); start_i--, d++);
        }
        d = 0;
        for(; end_i<wiki_text.length && !_is_period(wiki_text, end_i); end_i++, d++);
        if(d < 8 && wiki_text.slice(end_i+1, start_i+6) != "\n[...]"){
            end_i++;
            for(; end_i<wiki_text.length && !_is_period(wiki_text, end_i); end_i++, d++);
        }

        let extended_found_excerpt = wiki_text.slice(start_i+1, end_i+1).trim();

        if(extended_found_excerpt.startsWith("]")){
            extended_found_excerpt = extended_found_excerpt.slice(1).trim();
        }
        if(extended_found_excerpt.endsWith("[")){
            extended_found_excerpt = extended_found_excerpt.slice(0, -1).trim();
        }
        if(extended_found_excerpt.endsWith("[.")){
            extended_found_excerpt = extended_found_excerpt.slice(0, -2).trim();
        }

        question["found_excerpt"] = extended_found_excerpt;
    }

    return questions;
}


async function main(params = {
    "input_path": "data/retrieve_quantities.json",
    "output_path": "data/find_excerpt.json",
    "log_path": "data/logs/find_excerpt/",
    "wikidump_path": "data/wikipedia_dumps/",
}) {
    const questions = JSON.parse(fs.readFileSync(params.input_path));

    let questions_by_topic = {};
    for(let question of questions){
        if(questions_by_topic[question.topic] == undefined){
            questions_by_topic[question.topic] = [];
        }
        question["found_excerpt"] = null;
        questions_by_topic[question.topic].push(question);
    }

    for(let topic in questions_by_topic){
        find_excerpt_in_topic(topic, questions_by_topic[topic], path.join(params.wikidump_path, topic + ".txt"));
    }

    console.log("Done");
    fs.writeFileSync(params.output_path, JSON.stringify(questions));
}

export { main };
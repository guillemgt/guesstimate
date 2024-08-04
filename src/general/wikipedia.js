import https from "https"

const do_wiki_request = async (query) => {
	let query_strings = []
	for(var key in query){
		query_strings.push(key + "=" + encodeURIComponent(query[key]));
	}
	let query_string = query_strings.join("&");

	// console.log("Calling api @ ", "w/api.php?" + query_string)

    return new Promise((resolve, reject) => {
        https.request({
            hostname: "en.wikipedia.org",
            path: "/w/api.php?" + query_string,
            method: "GET",
            port: 443,
        }, (response) => {
            response.setEncoding('utf8');
            let data = '';

            response.on('data', (chunk) => {
                data += chunk;
            });

            response.on('end', () => {
                resolve(data);
            });
        }).on('error', (err) => {
            reject(err);
        }).end();
    });
}


const normalizeArticle = async (title, callback) => {
	const body = await do_wiki_request({
		"action": "query",
		"titles": title,
		"format": "json",
		"formatversion": 2,
	});
    
    try{
        var json = JSON.parse(body);
        if(json.query.pages.length > 0)
            return json.query.pages[0].title;
    }catch(e){
        console.log("[ERROR]", e);
    };
}

const normalizeArticles = async (titles, callback) => {
	const body = await do_wiki_request({
		"action": "query",
		"titles": titles.join("|"),
		"format": "json",
		"formatversion": 2,
	});
    
    try{
        var json = JSON.parse(body);
        let normalized_titles = [];
        for(let i=0; i<json.query.pages.length; i++){
            normalized_titles.push(json.query.pages[i].title);
        }
        return normalized_titles;
    }catch(e){
        console.log("[ERROR]", e);
    };
}

const isDisambiguation = async (title, callback) => {
    const body = await do_wiki_request({
		"action": "query",
        "prop": "categories",
		"titles": title,
		"format": "json",
		"formatversion": 2,
	});

    try{
        var json = JSON.parse(body);
        if(json.query.pages.length > 0){
            let categories = json.query.pages[0].categories;
            if(categories) for(let i=0; i<categories.length; i++){
                if(categories[i].title == "Category:All article disambiguation pages" || categories[i].title == "Category:All article disambiguation pages"){
                    return true;
                }
            }
            return false;
        }
    }catch(e){
        console.log("[ERROR]", e);
    };
}

const areDisambiguation = async (titles, callback) => {
    const body = await do_wiki_request({
		"action": "query",
        "prop": "categories",
		"titles": titles.join("|"),
		"format": "json",
		"formatversion": 2,
	});

    try{
        var json = JSON.parse(body);
        let titles_disambiguation = [];
        for(let i=0; i<json.query.pages.length; i++){
            let categories = json.query.pages[i].categories;
            if(categories)
                for(let j=0; j<categories.length; j++){
                    if(categories[j].title == "Category:All article disambiguation pages" || categories[j].title == "Category:All article disambiguation pages"){
                        titles_disambiguation.push(json.query.pages[i].title);
                    }
                }
        }
        return titles_disambiguation;
    }catch(e){
        console.log("[ERROR]", e);
    };
}

const query = async (queryTerm) => {
    return await do_wiki_request({
        "action": "parse",
        "prop": "text",
        "redirects": true,
        "format": "json",
        "page": queryTerm
    });
}

export { normalizeArticle, normalizeArticles, isDisambiguation, areDisambiguation, query };
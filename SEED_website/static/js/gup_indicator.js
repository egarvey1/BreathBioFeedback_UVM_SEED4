// Function to change heading background color
function gupIndicator(){
//    console.log("Changing the Circle style")
    document.getElementById("circle").style.display = 'none';
    document.getElementById("gup_star").style.display = 'block';
    document.getElementById("gup_star").delay(5000);
}

// Updates the size and color of the indicator circle
function changeIndicator(color, size){

    document.getElementById("circle").style.display = 'block';
    document.getElementById("gup_star").style.display = 'none';
    document.getElementById("circle").style.background = color;
    document.getElementById("circle").style.height = size;
    document.getElementById("circle").style.width = size;
}



// Accesses the most recent gup data
function get_gup_data(callback, since) {
    var data = {};
    if (since !== undefined) {
        data.since = since
    }
    $.ajax({
        url: "/gup_stat",
        type: "GET",
        data: data,
        dataType: "json",
        success: function(response) {
            if (callback !== undefined) {
                var gup_datas = [];
                for (var i in response) {

                    var gup_list = response[i];

                    var gup_data = {
			            id: gup_list[0],
                        timestamp: gup_list[1],
                        gup_status: gup_list[2],
                        breath_in_status: gup_list[3],
                        breath_out_status: gup_list[4]
                    };
                    gup_datas.push(gup_data);
                }
                callback(gup_datas);
            }
        }
    });
}

var latest_timestamp = "0";

//Accesses the most recent gup data from the database
function get_new_gup_data(callback) {

    get_gup_data(function(gups) {
        if (gups.length > 0) {
            latest_timestamp = gups[gups.length - 1].timestamp;
        }
        callback(gups);
    }, latest_timestamp)
}



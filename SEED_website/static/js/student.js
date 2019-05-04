
previous_indicator_size = 150;
previous_r = 122
previous_g = 173
previous_b = 255

original_indicator_size = 150;
original_r = 122
original_g = 173
original_b = 255

size_increment = 1;
r_increment = 1;
g_increment = 2;


//This is the function that constantly updates the webpage
function update() {
    get_new_gup_data(function(gups) {

        for (var i in gups) {
            var gup = gups[i];

            //Good for debugging
//                       console.log(gup);
//            console.log(gup.gup_status);
//            console.log(gup.breath_in_status);
//            console.log(gup.breath_out_status);

            if (gup.gup_status == 1) {
                console.log("Gup found")
                gupIndicator();
                gupIndicator();
                gupIndicator();
            }
            else if (gup.breath_in_status == 1) {
                console.log("Breath in detected")
                previous_r = previous_r - r_increment;
                previous_g = previous_g - g_increment;
                previous_indicator_size = previous_indicator_size+size_increment;

                //Prevents the gup indicator from getting too big
                if (previous_indicator_size > 400) {
                    previous_indicator_size = 400
                }


                color = 'rgb('+previous_r+','+previous_g+','+previous_b+')';
                size = previous_indicator_size;
                changeIndicator(color, size);
            }
            else if (gup.breath_out_status == 1) {
                console.log("breath out detected")
                previous_r = previous_r + r_increment;
                previous_g = previous_g + g_increment;
                previous_indicator_size = previous_indicator_size - size_increment;

                //Prevents the indicator from getting too small
                 if (previous_indicator_size < 80) {
                    previous_indicator_size = 80
                }

                color = 'rgb('+previous_r+','+previous_g+','+previous_b+')';
                size = previous_indicator_size;
                changeIndicator(color, size);
            }
            else {
                console.log("nothing above was detected")
                //No changes are made to the gup indicator
                color = 'rgb('+previous_r+','+previous_g+','+previous_b+')';
                changeIndicator(color, previous_indicator_size);
            }
        }
    });
}

//Activates when the page is loaded.  Sets the update interval for the website.  Currently set to 100 ms
$(document).ready(function() {
    update();
    setInterval(update, 100);
});

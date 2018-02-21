var map;
$(document).ready(function() {

 	// Set up map widget
 	options = {
 		map_id: "map",
 		zoom: 12
 	}
 	map = new LeafletPolylineWidget(options);

 	// Retrieve ambulances via AJAX
 	retrieveAmbulances(ambulance_id)

});

function retrieveAmbulances(ambulance_id) {

    $.ajax({
        type: 'GET',
        datatype: "json",
        url: APIBaseUrl + 'ambulance/' + ambulance_id + '/updates',

        fail: function (msg) {

            alert('Could not retrieve data from API:' + msg)

        },

        success: function (data) {

            console.log('Got data from API')

            addAmbulanceRoute(data)

        }

    })
        .done(function (data) {
            if (console && console.log) {
                console.log("Done retrieving ambulance data from API");
            }
        });

}

function addMarker(map, update) {

	// add marker
	map.addPoint(update.location.latitude, update.location.longitude, update.id, null)
		.bindPopup('<strong>' + ambulance_status[status] + '</strong><br/>@' + update.timestamp)
		.on('mouseover',
			function(e){
				// open popup bubble
				this.openPopup().on('mouseout',
					function(e){
						this.closePopup();
					});
			});
};

// Interact with widget to add an ambulance route
function addAmbulanceRoute(data) {

	// Add status markers
	// TODO: color depending on status

	updates = data.results;
	
	// First entry
	var lastStatus;
	if (updates.length >= 2) {

		// Retrieve last entry (first position)
		entry = updates[updates.length - 1];

		// add marker
		addMarker(map, entry);

		// entry status
		lastStatus = entry.status;

	}

	// Mid updates
	for (var i = updates.length - 2; i > 0; i--) {

		// Retrieve next entry
		entry = updates[i];

		if (entry.status != lastStatus) {

            // add marker
            addMarker(map, entry);

        }

		// entry status
		lastStatus = entry.status;

	}

	// Last entry
	if (updates.length > 0) {

		// Retrieve last entry (first position)
		entry = updates[0];

		// add marker
		addMarker(map, entry);

	}

	// Store data in an array
	var latlngs = [];
	data.results.forEach(function(update) {

		// push location
		var loc = update.location;
		latlngs.push([loc.latitude, loc.longitude]);

    });

	// Add line to map
	console.log('Adding line');
	map.addLine(latlngs, 1, "red", null);

	// Zoom to bounds
	console.log('Fitting bounds');
	map.fitBounds();

}
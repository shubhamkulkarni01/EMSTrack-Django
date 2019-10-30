import {logger} from './logger';

import noUiSlider from 'nouislider';
import 'nouislider/distribute/nouislider.css';

import {validateDateRange} from "./util";

let apiClient;
const vehicles = {};

// add initialization hook
add_init_function(init);

function segmentHistory(history, byStatus, byUser) {

    byStatus = byStatus || true; // split by status
    byUser = byUser || false;     // split by user

    const segments = [];
    const durations = [];
    const status = [];
    const user = [];

    let currentSegment = [];
    let lastPosition = null;
    const n = history.length;
    for (let i = n - 1; i >= 0; i--) {

		// current position
        const currentPosition = history[i];

        // distance?
		if (lastPosition != null) {

            let newUser = false;
            let newStatus = false;

            if (byUser && lastPosition.updated_by_username !== currentPosition.updated_by_username) {
			    newUser = true;
            }

            if (!newUser && byStatus && lastPosition.status !== currentPosition.status) {
			    newStatus = true;
			    // will break segment, add current position first
                const newCurrentPosition = Object.assign({}, currentPosition);
                newCurrentPosition.status = lastPosition.status;
                currentSegment.push(newCurrentPosition);
            }

			if (newUser || newStatus) {
                // terminate current segment
                durations.push(
                    new Date(currentSegment[currentSegment.length-1].timestamp) -
                    new Date(currentSegment[0].timestamp)
                );  // in miliseconds
                segments.push(currentSegment);
                status.push(lastPosition.status);
                user.push(lastPosition.updated_by_username);
                currentSegment = [];
            }
		}

		// add position to segment
		currentSegment.push(currentPosition);

		// update lastPosition
		lastPosition = currentPosition;

	}

	// anything left?
	if (currentSegment.length > 0) {
        // terminate last segment
        durations.push(
            new Date(currentSegment[currentSegment.length-1].timestamp) -
            new Date(currentSegment[0].timestamp)
        );  // in miliseconds
        segments.push(currentSegment);
        status.push(lastPosition.status);
        user.push(lastPosition.updated_by_username);
    }

	return [segments, durations, status, user];

}

function renderProgress(data, beginDate, endDate) {

    console.log(data);

     // clone durations
    const segments = data['segments'];
    const durations = [...data['durations']];
    const status = data['status'];

    console.log(segments);
    console.log(durations);
    console.log(status);

    // calculate offsets
    const n = status.length;
    const offsets = new Array(n);
    let beforeRange = true;
    const totalTime = endDate.getTime() - beginDate.getTime();
    for (let i = 0; i < n; i++) {

        const segment = segments[i];
        const currentOffset = (new Date(segment[0].timestamp)).getTime() - beginDate.getTime();
        offsets[i] = currentOffset;

        if (beforeRange && currentOffset >= 0) {
            // this is the first element in range
            beforeRange = false;
            if (i > 0 && currentOffset[i - 1] + durations[i - 1] >= 0) {
                // previous status extends in range, shift to zero to ensure continuity
                durations[i - 1] -= currentOffset[i - 1];
                currentOffset[i - 1] = 0;
            }
        }

        if (currentOffset > totalTime) {
            // simply break, out of range
            break;
        }

        if (currentOffset + durations[i] > totalTime) {
            // match end and break
            durations[i] -= (currentOffset + durations[i] - totalTime);
            break;
        }

    }

    // build progress bar
    let cursor = 0;
    let progress = '<div class="progress" style="height: 20px;">\n';
    for (let i = 0; i < n; i++) {

        // not in range yet
        if (offsets[i] < 0)
            continue;

        // out of range, break
        if (offsets[i] > totalTime)
            break;

        // in range, advance bar until start
        const start = 100 * (offsets[i] / totalTime);
        logger.log('debug', 'start = %s', start);
        if (start > cursor) {
            const delta = (start - cursor);
            progress += `<div class="progress-bar bg-light" role="progressbar" style="width: ${delta}%" aria-valuenow="${delta}" aria-valuemin="0" aria-valuemax="100"></div>\n`;
            cursor = start;
            logger.log('debug', 'delta = %s', delta);
        }

        // fill bar with duration fraction
        const fraction = (100 * (durations[i] / totalTime));
        const status_class = ambulance_css[status[i]]['class'];
        progress += `<div class="progress-bar bg-${status_class}" role="progressbar" style="width: ${fraction}%" aria-valuenow="${fraction}" aria-valuemin="0" aria-valuemax="100"></div>\n`;
        cursor += fraction;

        logger.log('debug', 'status = %s', status[i]);
        logger.log('debug', 'fraction = %s', fraction);
        logger.log('debug', 'cursor = %s', cursor);

    }

    progress += '</div>';
    // logger.log('debug', 'progress = %s', progress);

    return progress;

}

function renderVehicle(vehicle, beginDate, endDate) {

    // get history
    const history = vehicle['history'];

    // get element
    let element = $(`#vehicles_${vehicle['id']}`);
    if (element.length === 0) {
        // create element first
        element = $(
`<div class="row">
  <div class="col-2">
    <strong>${vehicle['identifier']}</strong>
  </div>
  <div class="col-10" id="vehicle_${vehicle['id']}">
  </div>
</div>`);
        $('#vehiclesTable').append(element);
    }

    // nothing to do?
    if (Object.entries(history).length === 0) {
        return;
    }

    // render progress
    const progress = renderProgress(history, beginDate, endDate);
    logger.log('debug', 'progress = %s', progress);

    console.log(element);

    // replace element content
    element.html(progress);

}

// initialization function
function init (client) {

    logger.log('info', '> report-vehicle-status.js');

    // set apiClient
    apiClient = client;

    // get parameters
    const urlParams = new URLSearchParams(window.location.search);

    // set beginDate
    const [beginDate, endDate, minTime] = validateDateRange(urlParams.get('beginDate'));
    logger.log('debug', 'beginDate = %s, endDate = %s', beginDate, endDate);

    const beginTime = beginDate.toTimeString().substr(0, 8);
    const endTime = endDate.toTimeString().substr(0, 8);
    logger.log('debug', 'beginTime = %s, endTime = %s', beginTime, endTime);

    // set datepickers
    $('#beginDate')
        .prop('value', beginDate.toISOString().substr(0, 10));

    // set range
    const range = beginDate.toISOString() + "," + endDate.toISOString();
    logger.log('debug', 'range = %j', range)

    // Retrieve vehicles
    apiClient.httpClient.get('ambulance/')
        .then( response => {

            // retrieve vehicles
            logger.log('debug', "Got vehicle data from API");

            // loop through vehicle records
            const requests = response.data.map( vehicle  => {

                logger.log('debug', 'Adding vehicle %s', vehicle['identifier']);

                // save vehicle
                vehicles[vehicle['id']] = vehicle;
                vehicles[vehicle['id']]['history'] = {};

                const url = 'ambulance/' + vehicle['id'] + '/updates/?filter=' + range;
                return apiClient.httpClient.get(url);

            });

            return Promise.all(requests);

        })
        .then( responses =>
            responses.forEach(
                response => {

                    // retrieve updates
                    const history = response.data;
                    if (history.length) {

                        // get id
                        const id = history[0]['ambulance_id'];

                        // segment by status and store
                        const [segments, durations, status, user] = segmentHistory(history, true, false);
                        vehicles[id]['history'] = {
                            'history': history,
                            'segments': segments,
                            'durations': durations,
                            'status': status,
                            'user': user
                        };

                    }

                }
        ))
        .then( () => {

            // add time scale to table
            let progress = '<div class="progress" style="height: 20px;">\n';
            const totalTime = endDate.getTime() - beginDate.getTime();

            const numberOfHours = Math.floor(totalTime / 1000 / 60 / 60);
            const delta = 100 * (1000 * 60 * 60 / totalTime);
            const labels = ['secondary', 'light'];
            for (let i = 0; i < numberOfHours; i++) {
                progress += `<div class="progress-bar bg-${labels[i % 2]} text-${labels[(i + 1) % 2]}" role="progressbar" style="width: ${delta}%" aria-valuenow="${delta}" aria-valuemin="0" aria-valuemax="100">${i}</div>\n`;
            }
            progress += '</div>';
            logger.log('debug', 'progress = %s', progress);

            $('#vehiclesTable').append(
`<div class="row">
  <div class="col-2">
    <strong>Time</strong>
  </div>
  <div class="col-10">
    ${progress}
  </div>
 </div>`);

            // add vehicles to page
            for (const vehicle of Object.values(vehicles)) {
                renderVehicle(vehicle, beginDate, endDate);
            }

            // enable generate report button
            $('#submitButton')
                .prop('disabled', false);

        })
        .catch( (error) => {
            logger.log('error', "'Failed to retrieve vehicles: %s ", error);
        });

}

$(function () {

    logger.log('info', 'beginning of ready function');

    // setup slider
    const slider = document.getElementById('slider-range');
    noUiSlider.create(slider, {
        start: [0, 24],
        step: 1/4,
        margin: 1,
        range: {
            'min': [0],
            'max': [24]
        },
        pips: {
            mode: 'count',
            values: 25,
            density: 4*24/100,
        }
    });

    logger.log('info', 'end of ready function');

});

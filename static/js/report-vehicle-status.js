import {logger} from './logger';

import {timeSplit, timeMerge, splitTimeToMillis} from "./util";

let map;
let apiClient;
const vehicles = {};

// add initialization hook
add_init_function(init);

// setdates
function validateDateRange(beginDate, beginTime, endTime) {

    // beginDate
    if (beginDate === null) {
        beginDate = new Date();
    } else
        beginDate = new Date(beginDate);

    // beginTime
    beginTime = timeSplit(beginTime);

    // endTime
    endTime = timeSplit(endTime, [23, 59, 59, 999]);

    // endTime < beginTime => endTime = beginTime + 1 hour
    if (splitTimeToMillis(...endTime) < splitTimeToMillis(...beginTime)) {
        endTime = [...beginTime];
        endTime[0] += 1;
    }

    // set dates
    beginDate.setHours(...beginTime);
    const endDate = new Date(beginDate);
    endDate.setHours(...endTime);

    const minTime = timeMerge(...beginTime);

    logger.log('debug', 'beginDate = %s, endDate = %s, minTime = %s', beginDate, endDate, minTime);

    return [beginDate, endDate, minTime];
}

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

// initialization function
function init (client) {

    logger.log('info', '> report-vehicle-status.js');

    // set apiClient
    apiClient = client;

    // get parameters
    const urlParams = new URLSearchParams(window.location.search);

    // set beginDate
    const [beginDate, endDate, minTime] = validateDateRange(
        urlParams.get('beginDate'), urlParams.get('beginTime'), urlParams.get('endTime'));
    logger.log('debug', 'beginDate = %s, endDate = %s, minTime = %s', beginDate, endDate,  minTime);

    const beginTime = beginDate.toTimeString().substr(0, 8);
    const endTime = endDate.toTimeString().substr(0, 8);
    logger.log('debug', 'beginTime = %s, endTime = %s', beginTime, endTime);

    // set datepickers
    $('#beginDate')
        .prop('value', beginDate.toISOString().substr(0, 10));

    $('#beginTime')
        .prop('value', beginTime)
        .change(function() {

            logger.log('debug', 'beginDate has changed!');

            const endTimeElement = $('#endTime');
            const endTime = endTimeElement.val();
            const beginTime = $( this ).val();
            logger.log('debug', 'beginDate = %s, beginTime = %s, endTime = %s', beginDate, beginTime, endTime);

            const [_beginDate, _endDate, _minTime] = validateDateRange(beginDate, beginTime, endTime);
            logger.log('debug', '_beginDate = %s, _endDate = %s, _minTime = %s', _beginDate, _endDate, _minTime);

            // replace endTime
            endTimeElement
                .prop('min', _minTime)
                .prop('value', _endDate.toTimeString().substr(0, 8));

        });

    $('#endTime')
        .prop('value', endTime)
        .prop('min', minTime);

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
                vehicles[vehicle['id']]['history'] = [];

                const url = 'ambulance/' + vehicle['id'] + '/updates/?filter=' + range;
                return apiClient.httpClient.get(url);

            });

            return Promise.all(requests);

        })
        .then( responses =>
            responses.forEach(
                response => {

                    // retrieve updates
                    const updates = response.data;
                    if (updates.length) {
                        const id = updates[0]['ambulance_id'];
                        vehicles[id]['history'] = updates;

                    }

                }
        ))
        .then( () => {

            // add time scale to table
            let cursor = 0;
            let progress = '<div class="progress" style="height: 20px;">\n';
            const totalTime = endDate.getTime() - beginDate.getTime();
            const startTime = beginDate.toTimeString().substr(0, 8)

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

            // add vehicles to table
            for (const vehicle of Object.values(vehicles)) {

                // get history
                const history = vehicle['history'];

                if (history.length === 0) {
                    // add empty row
                    $('#vehiclesTable').append(
`<div class="row">
  <div class="col-2">
    <strong>${vehicle['identifier']}</strong>
  </div>
  <div class="col-10">
  </div>
 </div>`);
                    continue;

                }

                // segment by status
                const [segments, durations, status, user] = segmentHistory(history, true, false);

                console.log(segments);
                console.log(durations);
                console.log(status);
                console.log(user);

                // calculate offsets
                const n = status.length;
                const offsets = new Array(n);
                for (let i = 0; i < n; i++) {
                    const segment = segments[i];
                    offsets[i] = (new Date(segment[0].timestamp)).getTime() - beginDate.getTime();
                }

                let cursor = 0;
                let progress = '<div class="progress" style="height: 20px;">\n';
                for (let i = 0; i < n; i++) {
                    // advance bar until start
                    const start = 100 * (offsets[i] / totalTime);
                    logger.log('debug', 'start = %s', start);
                    if (start > cursor) {
                        const delta = (start - cursor);
                        progress += `<div class="progress-bar bg-light" role="progressbar" style="width: ${delta}%" aria-valuenow="${delta}" aria-valuemin="0" aria-valuemax="100"></div>\n`;
                        cursor = start;
                        logger.log('debug', 'delta = %s', delta);
                    }
                    // fill barr with fraction
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

                $('#vehiclesTable').append(
`<div class="row">
  <div class="col-2">
    <strong>${vehicle['identifier']}</strong>
  </div>
  <div class="col-10">
    ${progress}
  </div>
 </div>`);

            }

            // enable geneate report button
            $('#submitButton')
                .prop('disabled', false);

        })
        .catch( (error) => {
            logger.log('error', "'Failed to retrieve vehicles: %s ", error);
        });

}

$(function () {

});

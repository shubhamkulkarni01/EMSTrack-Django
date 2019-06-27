/**
 * Location base class
 */
export class Location {

    constructor(location) {
        this.location = location;
    }

    static toText(location) {

        // format address
        let address = [location.number, location.street, location.unit].join(' ').trim();

        if (address !== "") {
            if (location.neighborhood !== "")
                address = [address, location.neighborhood].join(', ').trim();
        } else
            address += location.neighborhood.trim()

        if (address !== "")
            address = [address, location.city, location.state].join(', ').trim();
        else
            address = [location.city, location.state].join(', ').trim();

        address = [address, location.zipcode].join(' ').trim();
        address = [address, location.country].join(', ').trim();

        return address;
    }

    render() {

        // language=HTML
        return (
            `<div>
    <p class="my-0 py-0">
        <em>${translation_table['Address']}:</em>
    </p>
    <p class="my-0 py-0 text-right">
        ${Location.toText(this.location)}
    </p>
    <p class="my-0 py-0">
        <em>${translation_table['Type']}:</em>
        <span class="float-right">${location_type[this.location.type]}</span>
    </p>
</div>`
        );

    }

}
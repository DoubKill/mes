var Equip_filter = {

    data: function () {

        return {

            process: "",
            equip: "",
        }
    },

    methods: {

        processChanged: function () {

            this.getFirstPage();
        },
        equipChanged: function () {

            this.getFirstPage();
        },
        beforeGetData() {

            this.getParams['process'] = this.process;
            this.getParams['equip'] = this.equip;
        },
    }
};
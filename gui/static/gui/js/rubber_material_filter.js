var Rubber_Material_filter = {

    data: function () {

        return {
            stage_product_batch_no: "",
        }
    },

    methods: {

        stage_product_batch_noChanged: function () {

            this.getFirstPage();
        },
        beforeGetData() {
            this.getParams['stage_product_batch_no'] = this.stage_product_batch_no;
        },
    }
};
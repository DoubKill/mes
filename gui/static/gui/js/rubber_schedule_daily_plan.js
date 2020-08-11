;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableDataUrl: ProductDayPlansUrl,
                plan_data: null,
                // new Date(),
                equips: [],
                equip_no: "",
                stage_product_batch_no: "",
                stage_product_batch_nos: []
            }
        },
        created: function () {

            var app = this;
            axios.get(EquipUrl, {
                params: {
                    page_size: 100000000
                }
            }).then(function (response) {

                app.equips = response.data.results;
            }).catch(function (error) {

            });
            axios.get(RubberMaterialUrl, {

                params: {
                    page_size: 100000000
                }
            }).then(function (response) {

                app.stage_product_batch_nos = [];
                response.data.results.forEach(function (batching) {

                    if (app.stage_product_batch_nos.indexOf(batching.stage_product_batch_no) === -1) {

                        app.stage_product_batch_nos.push(batching.stage_product_batch_no)
                    }
                });
            }).catch(function (error) {

            });
        },
        methods: {

            queryDataChange: function () {

                this.currentChange(this.currentRow);
            },
            beforeGetData: function () {

                this.getParams["plan_data"] = this.plan_data;
                this.getParams["equip_no"] = this.equip_no;
                this.getParams["product_no"] = this.stage_product_batch_no
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();
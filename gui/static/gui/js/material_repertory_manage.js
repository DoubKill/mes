;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableDataUrl: MaterialRepertoryUrl,
                materialType:null,
                materialTypeOptions:[],
            }
        },
        created: function() {
            var app = this;
            axios.get(MaterialTypelUrl, {
            }).then(function (response) {
                app.materialTypeOptions = response.data.results;
            }).catch(function (error) {
            });
        },


        methods: {
            StandardFlagFormatter: function (row, column) {

                return this.StandardFlagChoice(row.standard_flag);
            },
            StandardFlagChoice: function (standard_flag) {
                switch (standard_flag) {
                    case true:
                        return "合格";
                    case false:
                        return "不合格";
                }
            },
            beforeGetData() {
                this.getParams["material_type_id"] = this.materialType;
            },
            materialTypeChange: function() {
                this.getFirstPage();
            },

            handleCurrentChange: function (val) {
                this.currentRow = val;
            },

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();
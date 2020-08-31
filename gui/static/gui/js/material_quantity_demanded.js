;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                tableDataUrl: MaterialQuantityDemandedUrl,
                search_time: new Date(),
                classes_arrangeOptions:[],
                rubber_recipe_no:null,
                classes_arrange:null,
            }
        },
        created: function() {
            var app = this;
            axios.get(ClassArrangelUrl, {
            }).then(function (response) {
                app.classes_arrangeOptions = response.data.results;
            }).catch(function (error) {
            });

        },


        methods: {
            beforeGetData() {
                this.getParams["plan_date"] = this.search_time;
                this.getParams["classes"] = this.classes_arrange;
                this.getParams["product_no"] = this.rubber_recipe_no;
            },
            handleCurrentChange: function (val) {
                this.currentRow = val;
            },
            search_timeChange: function () {
                this.getFirstPage();
            },
            classes_arrangeChange: function () {
                this.getFirstPage();
            },
            rubber_recipe_noChange: function () {
                this.getFirstPage();
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();
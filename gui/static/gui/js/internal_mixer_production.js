;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {
            return {
                tableData: [],
                getParams: {
                    page: 1,
                    search_date: [],
                    norms: null,
                    produce: null,
                    group: null,

                },
                normsList: [],
                produceList: [],
                groupList: [],
                dialogVisibleRubber: false,
                tableDataRubber: [],
                tableDataBAT:[],
                dialogVisibleBAT: false
            }
        },
        methods: {
            changeData() {
                console.log(this.getParams.search_date, 'getParams.search_date')
            },
            changeNorms() {
            },
            clickPrint() {
                this.clickViewRubber()
            },
            clickExcel() {
            },
            clickViewRubber() {
                this.dialogVisibleRubber = true

            },
            clickBAT() {
                this.dialogVisibleBAT = true
            },
            viewGraph() {
            }
        }
    }
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();
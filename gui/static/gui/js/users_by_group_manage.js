;(function () {

    var Main = {

        mixins: [BaseMixin, GroupsFilterMixin],
        data: function () {

            return {

                tableDataUrl: GroupUrl,
                groupsCurrentRow: null
            }
        },
        methods: {

            handleGroupsCurrentRowChange: function (row) {

                if(!row)
                    return;
                var app = this;
                this.groupsCurrentRow = row;
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();
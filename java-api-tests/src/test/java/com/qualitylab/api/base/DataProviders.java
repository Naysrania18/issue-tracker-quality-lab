package com.qualitylab.api.base;

import com.qualitylab.api.models.WorkflowState;
import java.util.ArrayList;
import java.util.List;
import org.testng.annotations.DataProvider;

/** TestNG data providers: one place for the tables of inputs that several tests share. */
public final class DataProviders {
    private DataProviders() {
    }

    /** Every (from, to) pair of workflow states with the expected answer. 25 rows. */
    @DataProvider(name = "allTransitions")
    public static Object[][] allTransitions() {
        List<Object[]> rows = new ArrayList<>();
        for (WorkflowState from : WorkflowState.values()) {
            for (WorkflowState to : WorkflowState.values()) {
                rows.add(new Object[] {from, to, from.canMoveTo(to)});
            }
        }
        return rows.toArray(new Object[0][]);
    }

    /** Invalid bodies for creating an issue, with a short description of what is wrong. */
    @DataProvider(name = "invalidIssues")
    public static Object[][] invalidIssues() {
        return new Object[][] {
            {"title too short", "ab", "Mail", "P3"},
            {"unknown priority", "A valid title", "Mail", "P9"},
            {"lowercase priority", "A valid title", "Mail", "p1"},
        };
    }
}

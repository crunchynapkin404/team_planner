
# Team Planner Shift Scheduling Specification

## 1. Incidents Shifts (Primary Coverage)

### **Shift Details**
- **Monday**: 08:00 - 17:00 (9 hours)
- **Tuesday**: 08:00 - 17:00 (9 hours)
- **Wednesday**: 08:00 - 17:00 (9 hours)
- **Thursday**: 08:00 - 17:00 (9 hours)
- **Friday**: 08:00 - 17:00 (9 hours)


### **Assignment Pattern**
- **Type**: Daily individual shifts (5 separate shifts per week)
- **Engineer Assignment**: Same engineer gets all 5 daily shifts for the week
- **Weekly Rotation**: New engineer starts each Monday
- **Duration per assignment**: Single day (9 hours each)

### **Scheduling Rules**
- Same engineer works Monday through Friday (gets 5 individual daily shifts)
- Each weekday is a separate shift assignment to the same engineer
- New engineer rotation starts each Monday
- Example: Engineer A gets Incidents-Monday, Incidents-Tuesday, Incidents-Wednesday, Incidents-Thursday, Incidents-Friday for Week 1

### **Shift Details**
- **Monday**: 08:00 - 17:00 (9 hours)
- **Tuesday**: 08:00 - 17:00 (9 hours)
- **Wednesday**: 08:00 - 17:00 (9 hours)
- **Thursday**: 08:00 - 17:00 (9 hours)
- **Friday**: 08:00 - 17:00 (9 hours)


## 2. Incidents-Standby Shifts (Secondary Coverage)

### **Shift Details**
- **Monday**: 08:00 - 17:00 (9 hours)
- **Tuesday**: 08:00 - 17:00 (9 hours)
- **Wednesday**: 08:00 - 17:00 (9 hours)
- **Thursday**: 08:00 - 17:00 (9 hours)
- **Friday**: 08:00 - 17:00 (9 hours)

### **Assignment Pattern**
- **Type**: Daily individual shifts (5 separate shifts per week)
- **Engineer Assignment**: Same engineer gets all 5 daily shifts for the week
- **Weekly Rotation**: New engineer starts each Monday
- **Duration per assignment**: Single day (9 hours each)

### **Scheduling Rules**
- Same engineer works Monday through Friday (gets 5 individual daily shifts)
- Each weekday is a separate shift assignment to the same engineer
- New engineer rotation starts each Monday
- Example: Engineer B gets Incidents-Standby-Monday, Incidents-Standby-Tuesday, Incidents-Standby-Wednesday, Incidents-Standby-Thursday, Incidents-Standby-Friday for Week 1

### **Coverage Details**
- **Primary Purpose**: Backup/additional coverage during high-demand periods
- **Assignment Condition**: Optional (when assigned, 2 engineers work simultaneously during business hours)
- Provides secondary support alongside primary Incidents engineer
- Both Incidents and Incidents-Standby engineers work simultaneously during 08:00-17:00
- Incidents-Standby engineer is the backup if primary engineer is unavailable
- **Fairness Tracking**: Separate rotation counter from Incidents shifts

## 3. Waakdienst Shifts (On-Call Coverage)

### **Coverage Times**
- **Purpose**: Cover ALL hours not covered by Incidents shifts + full weekends
- **Timezone**: europe/amsterdam

### **Weekly Schedule (Wednesday 17:00 to Wednesday 08:00)**
- **Wednesday Evening**: 17:00 - Thursday 08:00 (15 hours overnight) - NEW engineer starts
- **Thursday Evening**: 17:00 - Friday 08:00 (15 hours overnight) 
- **Friday Evening**: 17:00 - Saturday 08:00 (15 hours overnight)
- **Saturday**: 08:00 - Sunday 08:00 (24 hours full day)
- **Sunday**: 08:00 - Monday 08:00 (24 hours full day)
- **Monday**: 17:00 - Tuesday 08:00 (15 hours overnight)
- **Tuesday Evening**: 17:00 - Wednesday 08:00 (15 hours overnight) - OLD engineer ends

### **Assignment Pattern**
- **Type**: Daily individual shifts (7 separate shifts per week)
- **Engineer Assignment**: Same engineer gets all 7 daily shifts for the week
- **Weekly Rotation**: New engineer starts each Wednesday at 17:00, previous engineer ends Wednesday at 08:00
- **Duration**: 7 days (Wednesday 17:00 to next Wednesday 08:00)
- **Handover Time**: Wednesday between 08:00-17:00 (during Incidents coverage)

### **Scheduling Rules**
- Same engineer works Wednesday 17:00 through next Wednesday 08:00 (gets 7 individual daily shifts)
- Each day is a separate shift assignment to the same engineer
- On Wednesday: OLD engineer gets Tuesday-night-to-Wednesday-morning shift (ends 08:00), NEW engineer gets Wednesday-evening shift (starts 17:00)
- Handover occurs on Wednesday during business hours (08:00-17:00)
- Example: Engineer C gets Waakdienst-Wednesday-Evening, Waakdienst-Thursday-Evening, Waakdienst-Friday-Evening, Waakdienst-Saturday-Full, Waakdienst-Sunday-Full, Waakdienst-Monday-Evening, Waakdienst-Tuesday-Evening for Week 1

### **Coverage Gaps Eliminated**
- **No gaps**: Waakdienst covers exactly when Incidents doesn't
- **Weekday evenings/nights**: Covered by Waakdienst
- **Full weekends**: Covered by Waakdienst
- **Business hours (Mon-Fri 08:00-17:00)**: Covered by Incidents (not Waakdienst)



## Important Notes

1. **No Time Gaps**: Every hour of every day is covered by at least one engineer
2. **Timezone**: Europe/Amsterdam (CET/CEST)
3. **Fairness**: Each shift type maintains separate rotation counters
4. **Overlap**: During Wednesday handover, both outgoing and incoming Waakdienst engineers may overlap during Incidents hours for knowledge transfer
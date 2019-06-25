<?php

use Illuminate\Database\Seeder;
use App\Enums\SubscriptionType;
use App\Board;

class UsersTableSeeder extends Seeder
{
    const FIRST_NAMES = array('Phuong', 'Maximina', 'Moon', 'Brigitte', 'Lavonna', 'Maire', 'Nidia', 'Porsche', 'Glynis', 'Luigi', 'Dionne', 'Shayla', 'Annamaria', 'Mimi', 'Della', 'Lashandra', 'Raylene', 'Jonah', 'Jae', 'Thurman', 'Malorie', 'Lessie', 'Anton', 'Brent', 'Carmella', 'Lisbeth', 'Tegan', 'Jarrett', 'Sylvia', 'Jeffrey', 'Christin', 'Fritz', 'Roseann', 'Maritza', 'Caroll', 'Keiko', 'Gertie', 'Yung', 'Penney', 'Tatyana', 'Christiana', 'Paris', 'Moriah', 'Graciela', 'Johnna', 'Vance', 'Sherlyn', 'Hae', 'Millicent', 'Olevia', 'Caren', 'Darwin', 'Terrell', 'Clemente', 'Vanna', 'Dylan', 'Kristi', 'Alisha', 'Cheryll', 'Jaqueline', 'Granville', 'Tesha', 'Letha', 'Clifford', 'Ferdinand', 'Robert', 'Rozella', 'Renita', 'Louie', 'Tien', 'Hazel', 'Karma', 'Kerri', 'Jaleesa', 'Maude', 'Elmo', 'Donte', 'Antonietta', 'Pamila', 'Herlinda', 'Donya', 'Idalia', 'Consuela', 'Aleida', 'Mauricio', 'Ema', 'Kenneth', 'Curt', 'Tamie', 'Mitchel', 'Bailey', 'Darline', 'Mozelle', 'Enoch', 'Lauryn', 'Eliana', 'Tierra', 'Terina', 'Skye', 'Tatyana');
    const SURNAMES = array('Pulido', 'Vanhoy', 'Furst', 'Scism', 'Wooding', 'Kowalczyk', 'Oliveras', 'Canton', 'Hamamoto', 'Jolin', 'Dockstader', 'Hearns', 'Tusing', 'Arellano', 'Lozoya', 'Calhoun', 'Heath', 'Taff', 'Brummett', 'Mader', 'Eisenhower', 'Ballenger', 'Wiley', 'Bradford', 'Pearman', 'Vanhouten', 'Fawcett', 'Proper', 'Pitchford', 'Willer', 'Kott', 'Rivett', 'Pascarelli', 'Jutras', 'Lacy', 'Koziel', 'Sargent', 'Harn', 'Truehart', 'Ulman', 'Gaeta', 'Brister', 'Hungerford', 'Monaco', 'Northrop', 'Riebel', 'Hinnant', 'Truss', 'Bigler', 'Renn', 'Guse', 'Mcmillian', 'Colone', 'Kowalsky', 'Maglio', 'Urbina', 'Lark', 'Heer', 'Guthridge', 'Mallon', 'Antunez', 'Seay', 'Lombard', 'Collyer', 'Reidhead', 'Heatherington', 'Witter', 'Manigo', 'Yuhas', 'Amen', 'Corwin', 'Meneely', 'Baird', 'Guilford', 'Korando', 'Mcgarr', 'Kummer', 'Sabin', 'Redwood', 'Heald', 'Schuldt', 'Folks', 'Shick', 'Pilger', 'Ritzer', 'Stearns', 'Crosier', 'Stalvey', 'Horan', 'Paylor', 'Strite', 'Calbert', 'Lohmann', 'Luongo', 'Carberry', 'Marquis', 'Dezern', 'Allinder', 'Bomba', 'Mcnary');

    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        DB::table('users')->insert([
            'forename' => 'Tom',
            'middle_initials' => '',
            'surname' => 'Longridge',
            'email' => 'tomlongridge@gmail.com',
            'password' => bcrypt('p'),
            'email_verified_at' => new DateTime,
        ]);

        for ($i = 0; $i < 100; $i++) {
            $firstName = Arr::random(UsersTableSeeder::FIRST_NAMES);
            $surname = Arr::random(UsersTableSeeder::SURNAMES);
            DB::table('users')->insert([
                'forename' => $firstName,
                'middle_initials' => strtoupper(Str::random(1)),
                'surname' => $surname,
                'email' => "${firstName}.${surname}.${i}@gmail.com",
                'password' => rand(0, 1) ? bcrypt('p') : null,
                'email_verified_at' => new DateTime,
            ]);
        }
    }
}
